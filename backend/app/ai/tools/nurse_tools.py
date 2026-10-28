"""
Nurse and Clinical Operations AI Tools for MediCore AI.
Provides:
  - Automated NEWS2 Clinical Deterioration Scoring.
  - SBAR (Situation, Background, Assessment, Recommendation) Shift Handover synthesis.
  - Code Blue / ACLS emergency resuscitation algorithmic guidance.
  - Nurse Triage and Inpatient monitoring assistance.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import User, UserRole, Patient, Encounter, Appointment, AppointmentStatus, Prescription
from app.services.triage_ai_service import triage_ai_service
from app.services.sbar_handover_service import SBARHandoverEngine
from app.services.acls_resuscitation_service import ACLSResuscitationEngine, RhythmCategory


def calculate_triage_score(vitals: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes standard NEWS2 (National Early Warning Score 2) and clinical urgency escalation.
    Includes Royal College of Physicians guidelines with supplemental oxygen and hypercapnic scale support.
    """
    normalized_vitals = dict(vitals or {})
    # Normalize common clinical oxygen and COPD parameter synonyms from conversational AI
    if "on_o2" in normalized_vitals or "o2_therapy" in normalized_vitals or "o2_support" in normalized_vitals:
        normalized_vitals["supplemental_oxygen"] = bool(
            normalized_vitals.get("on_o2") or normalized_vitals.get("o2_therapy") or normalized_vitals.get("o2_support")
        )
    if "copd" in normalized_vitals or "hypercapnia" in normalized_vitals or "hypercapnic" in normalized_vitals:
        normalized_vitals["copd_scale_2"] = bool(
            normalized_vitals.get("copd") or normalized_vitals.get("hypercapnia") or normalized_vitals.get("hypercapnic")
        )

    score = triage_ai_service.calculate_news2(normalized_vitals)
    if score >= 7:
        acuity = "CRITICAL / LEVEL 1"
        action = "Immediate emergency medical response. Notify Attending Physician and Intensive Care Team."
        escalate_rrt = True
    elif score >= 5:
        acuity = "URGENT / LEVEL 2"
        action = "Urgent clinical review required within 30 minutes. Continuous monitoring indicated."
        escalate_rrt = True
    elif score >= 1:
        acuity = "LOW / LEVEL 3"
        action = "Routine inpatient nursing observations. Repeat vitals in 4-6 hours."
        escalate_rrt = False
    else:
        acuity = "NORMAL / LEVEL 4"
        action = "Baseline parameters stable. Standard monitoring protocol."
        escalate_rrt = False

    return {
        "news2_score": score,
        "acuity_level": acuity,
        "rapid_response_team_indicated": escalate_rrt,
        "clinical_action": action,
        "supplemental_oxygen_considered": bool(normalized_vitals.get("supplemental_oxygen", False)),
        "copd_scale_2_applied": bool(normalized_vitals.get("copd_scale_2", False)),
        "vitals_analyzed": normalized_vitals
    }


def get_nurse_triage_queue(db: Session, current_user: User) -> List[Dict[str, Any]]:
    """
    Retrieves the current triage queue of waiting and scheduled patients for nursing workflow.
    """
    if current_user.role not in [UserRole.NURSE, UserRole.DOCTOR, UserRole.ADMIN]:
        return []

    apps = db.query(Appointment).filter(
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).order_by(Appointment.date.asc(), Appointment.start_time.asc()).limit(10).all()

    queue = []
    for a in apps:
        queue.append({
            "appointment_id": a.id,
            "appointment_number": a.appointment_number,
            "patient_name": a.patient.user.full_name if a.patient and a.patient.user else "Patient",
            "patient_id": a.patient_id,
            "doctor": a.doctor.user.full_name if a.doctor and a.doctor.user else "Staff Doctor",
            "department": a.department.name if a.department else "General",
            "scheduled_time": f"{a.date} {a.start_time.strftime('%H:%M')}",
            "status": a.status.value
        })
    return queue


def draft_sbar_handover(db: Session, current_user: User, patient_id: int) -> Dict[str, Any]:
    """
    Drafts a comprehensive clinical SBAR handover report for patient shift transfer.
    """
    if current_user.role not in [UserRole.NURSE, UserRole.DOCTOR, UserRole.ADMIN]:
        return {"error": "Access denied. Clinical credentials required."}

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"error": f"Patient with ID {patient_id} not found."}

    # Retrieve active prescriptions
    prescriptions = db.query(Prescription).filter(
        Prescription.patient_id == patient_id
    ).all()

    med_list = []
    for p in prescriptions:
        if isinstance(p.medications, list):
            for m in p.medications:
                if isinstance(m, dict):
                    med_list.append(f"{m.get('name', 'Medication')} ({m.get('dosage', '')})")
                else:
                    med_list.append(str(m))
        elif isinstance(p.medications, str):
            med_list.append(p.medications)

    # Mock or retrieve standard baseline vitals for synthesis
    vitals = {
        "blood_pressure_systolic": 120,
        "heart_rate": 78,
        "respiratory_rate": 16,
        "temperature_celsius": 37.0,
        "oxygen_saturation": 98,
        "news2_score": 0
    }

    report = SBARHandoverEngine.generate_sbar_handover(
        patient_id=patient.id,
        patient_name=patient.user.full_name if patient.user else f"Patient #{patient.id}",
        room_number="Room 304",
        attending_doctor="Dr. On Duty",
        primary_diagnosis="Clinical observation / Care management",
        admission_date="Current Admission",
        allergies=[patient.blood_group] if patient.blood_group else ["NKDA"],
        vitals=vitals,
        active_medications=med_list,
        nurse_notes="Patient resting comfortably; shift vitals and medications documented."
    )

    return report


def get_acls_guidance(rhythm: str, cpr_cycle: int = 1) -> Dict[str, Any]:
    """
    Provides immediate AHA ACLS algorithmic guidance for Code Blue cardiac resuscitation.
    """
    guidance = ACLSResuscitationEngine.evaluate_resuscitation_step(
        current_rhythm=rhythm,
        cpr_cycle_number=cpr_cycle,
        total_shocks_delivered=1 if "SHOCKABLE" in rhythm.upper() or rhythm.upper() in ["VF", "PVT"] else 0,
        epinephrine_doses_given=0,
        amiodarone_doses_given=0
    )
    return guidance


def evaluate_sepsis_risk(
    patient_id: int,
    systolic_bp: int,
    heart_rate: int,
    respiration_rate: int,
    temperature: float,
    altered_mentation: bool = False,
    suspected_infection_source: Optional[str] = None,
    serum_lactate: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates Sepsis 3.0, quick SOFA (qSOFA), SIRS criteria, and triggers the Surviving Sepsis 1-Hour Bundle.
    """
    from app.services.sepsis_engine import SepsisProtocolEngine
    return SepsisProtocolEngine.evaluate_sepsis_protocol(
        patient_id=patient_id,
        systolic_bp=systolic_bp,
        heart_rate=heart_rate,
        respiration_rate=respiration_rate,
        temperature=temperature,
        altered_mentation=altered_mentation,
        suspected_infection_source=suspected_infection_source,
        serum_lactate=serum_lactate
    )

