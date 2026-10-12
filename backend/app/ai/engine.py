import json
import logging
import time
import re
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import User, UserRole, AIConversation, AIMessage
from app.ai.gateway import ai_gateway
from app.ai.tools.patient_tools import (
    search_doctors, get_available_slots, create_appointment, 
    get_patient_appointments, cancel_appointment, search_hospital_knowledge,
    get_patient_prescriptions as get_patient_rx_patient
)
from app.ai.tools.doctor_tools import (
    summarize_patient_history, summarize_document, 
    search_hospital_clinical_guidelines,
    get_patient_prescriptions as get_patient_rx_doctor
)
from app.ai.tools.nurse_tools import (
    calculate_triage_score, get_nurse_triage_queue,
    draft_sbar_handover, get_acls_guidance
)
from app.ai.tools.admin_tools import (
    get_appointment_statistics, get_department_statistics, 
    get_doctor_workload, get_inventory_alerts
)

logger = logging.getLogger("medicore.ai")

class AIEngine:
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        self.model_name = settings.GEMINI_MODEL
        if self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise RuntimeError(
                    "FATAL: AI_PROVIDER is set to 'gemini' but GEMINI_API_KEY is not configured. "
                    "Silent fallback to mock is strictly disabled."
                )
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.genai = genai
                logger.info(f"Gemini AI Engine successfully initialized with model {self.model_name}")
            except Exception as e:
                logger.error(f"FATAL: Failed to initialize Gemini API with model {self.model_name}: {e}")
                raise RuntimeError(
                    f"Gemini initialization failure: {e}. MediCore AI will NOT silently switch to mock mode when AI_PROVIDER='gemini'."
                ) from e
        elif self.provider == "mock":
            logger.info("AIEngine initialized in explicit local mock mode (AI_PROVIDER=mock).")
        else:
            raise RuntimeError(f"Invalid AI_PROVIDER='{self.provider}'. Must be 'gemini' or 'mock'.")

    def process_chat(
        self,
        db: Session,
        current_user: User,
        message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        start_time = time.time()

        # 1. AI Gateway Kill Switch Check (Global & Feature-level)
        if ai_gateway.is_kill_switch_active("chat"):
            reason = (
                ai_gateway._feature_kill_switches.get("chat")
                or ai_gateway._kill_switch_reason
                or "Administrative Directive"
            )
            logger.warning(f"AI Chat intercepted: Kill switch active ({reason})")
            return {
                "conversation_id": conversation_id or 0,
                "message": (
                    f"⚠️ **AI Clinical Operations Suspended**\n\n"
                    f"The MediCore AI conversational assistant has been temporarily paused by an administrative security directive ({reason}).\n\n"
                    f"Core electronic health records, manual prescription writing, and direct hospital services remain fully functional."
                ),
                "tool_calls": None,
                "sources": None
            }

        # 2. Rate Limiting Enforcement
        if not ai_gateway._check_rate_limit(current_user.id if current_user else None):
            return {
                "conversation_id": conversation_id or 0,
                "message": (
                    "⚠️ **Query Rate Limit Exceeded**\n\n"
                    "You have exceeded the permitted query threshold for clinical AI operations (30 requests/minute). "
                    "Please wait a moment before sending additional queries to ensure service reliability."
                ),
                "tool_calls": None,
                "sources": None
            }

        # 3. Prompt Injection Defense & Sanitization
        sanitized_msg, flagged, reason = ai_gateway.sanitize_untrusted_input(message)
        if flagged:
            latency_ms = (time.time() - start_time) * 1000
            ai_gateway._record_metric(
                db=db,
                user_id=current_user.id if current_user else None,
                feature_name="ai_chat",
                latency_ms=latency_ms,
                status_code=400,
                tokens=len(message.split()) * 2,
                flagged=True,
                security_reason=reason
            )
            return {
                "conversation_id": conversation_id or 0,
                "message": (
                    f"🛡️ **Security Interception Notice**\n\n"
                    f"Your input contained an unauthorized prompt manipulation or security override pattern ({reason}).\n\n"
                    f"MediCore AI enforces strict HIPAA and NIST cybersecurity boundaries. "
                    f"System instructions and clinical contexts cannot be altered or disclosed. "
                    f"This security event has been logged to the immutable compliance audit vault."
                ),
                "tool_calls": None,
                "sources": None
            }

        # 4. Fetch or create conversation
        if conversation_id:
            conv = db.query(AIConversation).filter(
                AIConversation.id == conversation_id,
                AIConversation.user_id == current_user.id
            ).first()
        else:
            conv = None

        if not conv:
            conv = AIConversation(
                user_id=current_user.id,
                role_context=current_user.role,
                title=sanitized_msg[:50]
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # Record User Message
        user_msg = AIMessage(
            conversation_id=conv.id,
            sender="USER",
            content=sanitized_msg
        )
        db.add(user_msg)
        db.commit()

        # 5. Execute Intent Dispatcher with Strict Role Permissions
        tool_calls = []
        sources = []
        reply_text = ""

        m_lower = sanitized_msg.lower()

        if current_user.role == UserRole.PATIENT:
            reply_text, tool_calls, sources = self._handle_patient_intent(db, current_user, sanitized_msg, m_lower)
        elif current_user.role == UserRole.DOCTOR:
            reply_text, tool_calls, sources = self._handle_doctor_intent(db, current_user, sanitized_msg, m_lower)
        elif current_user.role == UserRole.NURSE:
            reply_text, tool_calls, sources = self._handle_nurse_intent(db, current_user, sanitized_msg, m_lower)
        elif current_user.role == UserRole.ADMIN:
            reply_text, tool_calls, sources = self._handle_admin_intent(db, current_user, sanitized_msg, m_lower)
        else:
            reply_text = "Hello, I am MediCore AI. How may I assist your clinical or operational workflow today?"

        # Save Assistant Message
        assistant_msg = AIMessage(
            conversation_id=conv.id,
            sender="ASSISTANT",
            content=reply_text,
            tool_calls=tool_calls if tool_calls else None,
            tool_results=sources if sources else None
        )
        db.add(assistant_msg)
        db.commit()

        # 6. Record Telemetry Metric in AIGovernanceMetric
        latency_ms = (time.time() - start_time) * 1000
        total_tokens = (len(sanitized_msg.split()) + len(reply_text.split())) * 2
        ai_gateway._record_metric(
            db=db,
            user_id=current_user.id if current_user else None,
            feature_name="ai_chat",
            latency_ms=latency_ms,
            status_code=200,
            tokens=total_tokens,
            flagged=False
        )

        return {
            "conversation_id": conv.id,
            "message": reply_text,
            "tool_calls": tool_calls,
            "sources": sources
        }

    def _handle_patient_intent(self, db: Session, user: User, raw_msg: str, msg: str):
        tool_calls = []
        sources = []

        # 1. Emergency safety check
        if any(w in msg for w in ["heart attack", "can't breathe", "severe bleeding", "unconscious", "emergency", "911"]):
            return (
                "⚠️ **URGENT EMERGENCY ALERT**\n\n"
                "If you or someone nearby is experiencing life-threatening symptoms (such as severe chest pain, inability to breathe, or loss of consciousness), **call 911 immediately** or proceed to the nearest emergency room.\n\n"
                "MediCore AI is an administrative and scheduling assistant and does not provide emergency triage.",
                [], []
            )

        # 2. View active prescriptions
        if any(w in msg for w in ["prescription", "prescriptions", "medication", "medications", "my meds", "drugs"]):
            tool_calls.append({"tool": "get_patient_prescriptions", "parameters": {}})
            rx_list = get_patient_rx_patient(db, user)
            if not rx_list:
                return (
                    "You do not have any active prescriptions recorded in your MediCore chart. "
                    "When your physician issues a prescription, it will appear here with dosage and refill instructions.",
                    tool_calls, sources
                )

            reply = f"Here are your active prescription records ({len(rx_list)} found):\n\n"
            for rx in rx_list:
                med_info = rx["medications"]
                if isinstance(med_info, list):
                    med_summary = ", ".join([f"{m.get('name', '')} ({m.get('dosage', '')})" if isinstance(m, dict) else str(m) for m in med_info])
                else:
                    med_summary = str(med_info)

                reply += f"- **Rx #{rx['prescription_id']}**: {med_summary}\n"
                if rx.get("instructions"):
                    reply += f"  • *Directions*: {rx['instructions']}\n"
                reply += f"  • *Prescriber*: {rx['doctor']} | *Date*: {rx['date']}\n"
            reply += "\n💡 *Always follow your physician's exact directions. Contact your pharmacy or physician for refill inquiries.*"
            return reply, tool_calls, sources

        # 3. Search Doctors & Slots
        if "cardio" in msg or "doctor" in msg or "specialist" in msg or ("appointment" in msg and "need" in msg):
            dept = "Cardiology" if "cardio" in msg else ("Neurology" if "neuro" in msg else "Orthopedics")
            tool_calls.append({"tool": "search_doctors", "parameters": {"department": dept}})
            docs = search_doctors(db, user, department=dept)
            if docs:
                chosen_doc = docs[0]
                target_date = (date.today() + timedelta(days=1)).isoformat()
                tool_calls.append({"tool": "get_available_slots", "parameters": {"doctor_id": chosen_doc["doctor_id"], "date": target_date}})
                slots_res = get_available_slots(db, user, chosen_doc["doctor_id"], target_date)
                avail = slots_res.get("available_slots", [])[:3]

                reply = (
                    f"✓ Found {chosen_doc['department']} specialist **{chosen_doc['name']}** ({chosen_doc['specialization']}).\n\n"
                    f"Consultation Fee: ${chosen_doc['fee']:.2f} | Rating: ⭐ {chosen_doc['rating']}\n\n"
                    f"**Available slots for tomorrow ({target_date}):**\n"
                )
                for s in avail:
                    reply += f"- 🕒 **{s}**\n"
                reply += "\nWould you like me to reserve one of these slots for you? Simply reply with the desired time slot."
                return reply, tool_calls, sources

        # 4. View appointments
        if "my appointment" in msg or "show appointments" in msg or "upcoming" in msg:
            tool_calls.append({"tool": "get_patient_appointments", "parameters": {}})
            apps = get_patient_appointments(db, user)
            if not apps:
                return "You do not have any scheduled appointments at this time.", tool_calls, sources

            reply = f"Here are your appointments on record ({len(apps)} found):\n\n"
            for a in apps[:4]:
                reply += f"- **{a['appointment_number']}**: Dr. {a['doctor']} ({a['department']}) on **{a['date']}** at **{a['start_time']}** [Status: `{a['status']}`]\n"
            return reply, tool_calls, sources

        # 5. Cancel appointment
        if "cancel" in msg and "appointment" in msg:
            apps = get_patient_appointments(db, user)
            if apps:
                target = apps[0]
                tool_calls.append({"tool": "cancel_appointment", "parameters": {"appointment_id": target["appointment_id"]}})
                cancel_res = cancel_appointment(db, user, target["appointment_id"], reason="Patient requested cancellation via AI")
                return f"✓ Confirmed: Your appointment **{target['appointment_number']}** with Dr. {target['doctor']} on {target['date']} has been cancelled.", tool_calls, sources
            return "You do not have any active appointments to cancel.", tool_calls, sources

        # 6. Hospital Policy / RAG (Visiting hours, Insurance, etc.)
        if any(w in msg for w in ["visit", "policy", "insurance", "hours", "document", "bring", "cost"]):
            tool_calls.append({"tool": "search_hospital_knowledge", "parameters": {"query": raw_msg}})
            rag_chunks = search_hospital_knowledge(db, user, raw_msg)
            if rag_chunks:
                top_chunk = rag_chunks[0]
                sources.append({"title": top_chunk["document_title"], "category": top_chunk["category"]})
                reply = (
                    f"{top_chunk['content']}\n\n"
                    f"📌 *Source: {top_chunk['document_title']} ({top_chunk['category']})*"
                )
                return reply, tool_calls, sources

        return (
            "I can help you search for specialists, check availability, view active prescriptions, "
            "manage appointments, or answer hospital policy questions. How can I assist you?",
            tool_calls, sources
        )

    def _handle_doctor_intent(self, db: Session, user: User, raw_msg: str, msg: str):
        tool_calls = []
        sources = []

        # Check for prescription query
        if "prescription" in msg or "medication" in msg or "rx" in msg:
            match = re.search(r"patient\s*#?(\d+)|id\s*[:=]?\s*(\d+)", msg)
            if match:
                pid = int(match.group(1) or match.group(2))
                tool_calls.append({"tool": "get_patient_prescriptions", "parameters": {"patient_id": pid}})
                res = get_patient_rx_doctor(db, user, pid)
                if res.get("error"):
                    return f"⚠️ **Prescription Lookup Notice**: {res['error']}", tool_calls, sources

                prescriptions = res.get("prescriptions", [])
                if not prescriptions:
                    return f"No active prescriptions found on file for patient {res.get('patient_name', pid)}.", tool_calls, sources

                reply = f"**Prescriptions for {res['patient_name']} (Patient ID: {pid})**:\n\n"
                for p in prescriptions:
                    meds = p["medications"]
                    if isinstance(meds, list):
                        med_str = ", ".join([f"{m.get('name', '')} {m.get('dosage', '')}" if isinstance(m, dict) else str(m) for m in meds])
                    else:
                        med_str = str(meds)
                    status_badge = "ACTIVE" if p["is_active"] else "INACTIVE"
                    reply += f"- **Rx #{p['prescription_id']}** [`{status_badge}`]: {med_str}\n"
                    if p.get("instructions"):
                        reply += f"  • *Instructions*: {p['instructions']}\n"
                    reply += f"  • *Issued*: {p['created_at']}\n"
                return reply, tool_calls, sources
            else:
                return (
                    "To view a patient's active prescriptions, please specify the patient identifier (e.g. 'Show prescriptions for patient 1').",
                    tool_calls, sources
                )

        # Patient history / clinical summary
        if "patient" in msg or "history" in msg or "summary" in msg:
            match = re.search(r"patient\s*#?(\d+)|id\s*[:=]?\s*(\d+)", msg)
            if match:
                pid = int(match.group(1) or match.group(2))
                tool_calls.append({"tool": "summarize_patient_history", "parameters": {"patient_id": pid}})
                summary = summarize_patient_history(db, user, patient_id=pid)
                if summary.get("error"):
                    return f"⚠️ **Authorization / Clinical Lookup Notice**: {summary['error']}", tool_calls, sources

                reply = (
                    f"**Clinical Summary for {summary['patient_name']} (Patient ID: {summary['patient_id']})**\n\n"
                    f"- **DOB**: {summary['dob']} | **Blood Group**: {summary['blood_group']}\n"
                    f"- **Known Conditions**: {summary['medical_history']}\n"
                    f"- **Recent Clinical Documents**: {summary['recent_documents_count']} on file\n"
                )
                for d in summary.get("document_summaries", []):
                    reply += f"  • {d}\n"
                reply += f"\n⚠️ *{summary['clinical_disclaimer']}*"
                return reply, tool_calls, sources
            else:
                return (
                    "To generate a clinical summary, please specify the patient identifier from your consultation roster (e.g., 'Summarize patient 10'). "
                    "Access is restricted to patients with whom you have an active or scheduled clinical encounter.",
                    tool_calls, sources
                )

        if "guideline" in msg or "policy" in msg:
            tool_calls.append({"tool": "search_hospital_clinical_guidelines", "parameters": {"query": raw_msg}})
            res = search_hospital_clinical_guidelines(db, user, raw_msg)
            if res:
                return f"**Clinical Guideline Reference**:\n\n{res[0]['content']}\n\n*Source: {res[0]['document_title']}*", tool_calls, res

        return (
            "Doctor Assistant active. You can ask for patient history digests, document summaries, "
            "active prescription lookups, or clinical hospital protocol searches. All outputs require clinical verification.",
            tool_calls, sources
        )

    def _handle_nurse_intent(self, db: Session, user: User, raw_msg: str, msg: str):
        tool_calls = []
        sources = []

        # 1. NEWS2 / Triage evaluation
        if any(w in msg for w in ["triage", "news2", "vitals", "deterioration", "score"]):
            # Extract sample vitals if present or provide calculation guide
            sbp_match = re.search(r"bp\s*[:=]?\s*(\d+)", msg)
            hr_match = re.search(r"hr\s*[:=]?\s*(\d+)|pulse\s*[:=]?\s*(\d+)", msg)
            rr_match = re.search(r"rr\s*[:=]?\s*(\d+)", msg)
            spo2_match = re.search(r"spo2\s*[:=]?\s*(\d+)|o2\s*[:=]?\s*(\d+)", msg)

            if sbp_match or hr_match or rr_match or spo2_match:
                vitals = {
                    "blood_pressure_systolic": int(sbp_match.group(1)) if sbp_match else 120,
                    "heart_rate": int(hr_match.group(1) or hr_match.group(2)) if hr_match else 75,
                    "respiratory_rate": int(rr_match.group(1)) if rr_match else 16,
                    "oxygen_saturation": int(spo2_match.group(1) or spo2_match.group(2)) if spo2_match else 98,
                }
                tool_calls.append({"tool": "calculate_triage_score", "parameters": {"vitals": vitals}})
                result = calculate_triage_score(vitals)
                reply = (
                    f"**NEWS2 Clinical Assessment**\n\n"
                    f"- **Score**: **{result['news2_score']}** | Acuity: `{result['acuity_level']}`\n"
                    f"- **Clinical Escalation**: {result['clinical_action']}\n"
                    f"- **Vitals Analyzed**: BP {vitals['blood_pressure_systolic']} mmHg, HR {vitals['heart_rate']} bpm, RR {vitals['respiratory_rate']}/min, SpO2 {vitals['oxygen_saturation']}%\n\n"
                    f"⚠️ *Early warning score calculated strictly for nursing decision support.*"
                )
                return reply, tool_calls, sources
            else:
                return (
                    "**NEWS2 Triage Assistant**: Enter patient vitals to calculate risk score (e.g. 'Triage score for BP 90, HR 125, RR 26, SpO2 91'). "
                    "NEWS2 triggers early warning alarms for sepsis and respiratory failure.",
                    tool_calls, sources
                )

        # 2. SBAR Shift Handover
        if any(w in msg for w in ["sbar", "handover", "shift", "transfer"]):
            match = re.search(r"patient\s*#?(\d+)|id\s*[:=]?\s*(\d+)", msg)
            if match:
                pid = int(match.group(1) or match.group(2))
                tool_calls.append({"tool": "draft_sbar_handover", "parameters": {"patient_id": pid}})
                sbar = draft_sbar_handover(db, user, pid)
                if sbar.get("error"):
                    return f"⚠️ **SBAR Generation Error**: {sbar['error']}", tool_calls, sources

                sbar_root = sbar.get("sbar", sbar)
                sit = sbar_root.get("situation", {})
                bak = sbar_root.get("background", {})
                asm = sbar_root.get("assessment", {})
                rec = sbar_root.get("recommendation", {}).get("action_items_for_incoming_shift", [])

                reply = (
                    f"📋 **Standardized Clinical SBAR Handover (Patient #{pid})**\n\n"
                    f"**[S] Situation**:\n"
                    f"- {sit['current_status_summary']}\n\n"
                    f"**[B] Background**:\n"
                    f"- Diagnosis: {bak['primary_diagnosis']} | Allergies: {', '.join(bak['documented_allergies'])}\n\n"
                    f"**[A] Assessment**:\n"
                    f"- Stability: `{asm['clinical_stability_risk']}` (NEWS2: {asm['news2_deterioration_score']})\n"
                    f"- Active Meds: {', '.join(asm['active_medication_regimen']) or 'None'}\n\n"
                    f"**[R] Recommendation**:\n"
                )
                for r in rec[:3]:
                    reply += f"- • {r}\n"
                return reply, tool_calls, sources
            else:
                return (
                    "To generate a structured SBAR shift handover, please specify the patient ID (e.g. 'Draft SBAR for patient 1').",
                    tool_calls, sources
                )

        # 3. ACLS / Code Blue Emergency Guidance
        if any(w in msg for w in ["acls", "code blue", "arrest", "resuscitation", "v-fib", "asystole"]):
            rhythm = "VENTRICULAR_FIBRILLATION" if any(w in msg for w in ["v-fib", "vf", "shockable"]) else "ASYSTOLE"
            tool_calls.append({"tool": "get_acls_guidance", "parameters": {"rhythm": rhythm}})
            acls = get_acls_guidance(rhythm=rhythm)
            reply = (
                f"🚨 **AHA ACLS Emergency Resuscitation Guidance**\n\n"
                f"- **Rhythm Classification**: `{acls['rhythm_category']}` ({rhythm})\n"
                f"- **Shock Indicated**: {'⚡ YES — 200J Biphasic Shock' if acls['shock_indicated'] else '❌ NO SHOCK — Continue CPR'}\n\n"
                f"**Immediate Clinical Actions:**\n"
            )
            for act in acls.get("immediate_actions", []):
                reply += f"- • {act}\n"
            if acls.get("medications_due"):
                reply += "\n**Medications Due:**\n"
                for med in acls["medications_due"]:
                    reply += f"- 💉 **{med['drug']}**: {med['dose']} ({med['route']})\n"
            return reply, tool_calls, sources

        # 4. Triage Queue
        if any(w in msg for w in ["queue", "waiting", "roster", "patients"]):
            tool_calls.append({"tool": "get_nurse_triage_queue", "parameters": {}})
            queue = get_nurse_triage_queue(db, user)
            if not queue:
                return "The nurse triage queue is currently clear. No patients awaiting triage intake.", tool_calls, sources

            reply = f"**Current Nurse Triage Queue ({len(queue)} patients awaiting intake):**\n\n"
            for q in queue:
                reply += f"- **{q['patient_name']}** (ID: {q['patient_id']}) -> Dr. {q['doctor']} [{q['department']}] scheduled at {q['scheduled_time']}\n"
            return reply, tool_calls, sources

        return (
            "Nursing Operations Assistant active. I can compute NEWS2 clinical deterioration scores, "
            "generate standardized SBAR shift handovers, look up ACLS resuscitation algorithms, or display the waiting triage queue.",
            tool_calls, sources
        )

    def _handle_admin_intent(self, db: Session, user: User, raw_msg: str, msg: str):
        tool_calls = []
        sources = []

        if "inventory" in msg or "stock" in msg or "low" in msg:
            tool_calls.append({"tool": "get_inventory_alerts", "parameters": {}})
            alerts = get_inventory_alerts(db, user)
            reply = f"**Hospital Inventory Alerts ({len(alerts)} items requiring attention):**\n\n"
            for item in alerts:
                reply += f"- **{item['item_name']}**: {item['quantity']} {item['unit']} remaining (Reorder Level: {item['reorder_level']}) - Status: `{item['status']}`\n"
            return reply, tool_calls, sources

        if "appointment" in msg or "how many" in msg or "stats" in msg or "stat" in msg:
            tool_calls.append({"tool": "get_appointment_statistics", "parameters": {}})
            stats = get_appointment_statistics(db, user)
            reply = (
                f"**Hospital Appointment Analytics:**\n\n"
                f"- Total Records: **{stats['total_appointments']}**\n"
                f"- Today's Scheduled: **{stats['today_appointments']}**\n"
                f"- Confirmed: **{stats['confirmed']}**\n"
                f"- Completed: **{stats['completed']}**\n"
                f"- Cancelled: **{stats['cancelled']}** ({stats['cancellation_rate_percent']}% rate)\n"
            )
            return reply, tool_calls, sources

        if "workload" in msg or "doctor" in msg:
            tool_calls.append({"tool": "get_doctor_workload", "parameters": {}})
            wl = get_doctor_workload(db, user)
            reply = "**Physician Workload Distribution (Top Active Doctors):**\n\n"
            for d in wl[:5]:
                reply += f"- **{d['doctor_name']}** ({d['department']}): {d['appointments_assigned']} consultations | Rating: ⭐ {d['rating']}\n"
            return reply, tool_calls, sources

        if "ai" in msg or "kill switch" in msg or "gateway" in msg or "status" in msg:
            is_active = ai_gateway.is_kill_switch_active()
            reply = (
                f"**MediCore AI Gateway Operational Status**:\n\n"
                f"- Provider: `{ai_gateway.provider}`\n"
                f"- Model: `{ai_gateway.model_name}`\n"
                f"- Global Kill Switch: `{'ACTIVATED (PAUSED)' if is_active else 'DEACTIVATED (HEALTHY)'}`\n"
                f"- Rate Limit: `{ai_gateway.MAX_REQUESTS_PER_WINDOW} req / {ai_gateway.RATE_LIMIT_WINDOW_SEC}s`\n"
                f"- Prompt Sanitizer: `ACTIVE (Perimeter Defense Enabled)`\n"
            )
            return reply, tool_calls, sources

        return (
            "Admin Operations Assistant active. You can query appointment metrics, inventory alerts, "
            "department utilization, physician workload, or AI gateway governance telemetry.",
            tool_calls, sources
        )

ai_engine = AIEngine()
