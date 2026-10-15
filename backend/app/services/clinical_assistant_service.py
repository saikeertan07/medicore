"""
Feature 1 — Unified AI Clinical Assistant Service
Provides comprehensive, authorized clinical synthesis for doctors and nurses.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Doctor, Appointment, Encounter, 
    EncounterVitals, ClinicalNote, ClinicalDiagnosis, Prescription, 
    LabOrder, LabResult, MedicalDocument
)
from app.ai.gateway import ai_gateway


class ClinicalAssistantService:
    def synthesize_patient_record(self, db: Session, clinician: User, patient_id: int) -> Dict[str, Any]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

        # Care relationship check
        if clinician.role == UserRole.DOCTOR and clinician.doctor_profile:
            doc_id = clinician.doctor_profile.id
            has_appt = db.query(Appointment).filter(
                Appointment.doctor_id == doc_id, 
                Appointment.patient_id == patient_id
            ).first()
            has_enc = db.query(Encounter).filter(
                Encounter.attending_doctor_id == doc_id,
                Encounter.patient_id == patient_id
            ).first()
            if not has_appt and not has_enc:
                # Check department coverage
                dept_id = clinician.doctor_profile.department_id
                dept_match = db.query(Appointment).join(Doctor).filter(
                    Appointment.patient_id == patient_id,
                    Doctor.department_id == dept_id
                ).first()
                if not dept_match:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. You do not have an active care relationship with this patient."
                    )

        # 1. Collect longitudinal medical facts
        demographics = {
            "patient_id": patient.id,
            "patient_number": patient.patient_number,
            "name": patient.display_name,
            "dob": str(patient.date_of_birth) if patient.date_of_birth else "Not documented",
            "gender": patient.gender or "Unknown",
            "blood_group": patient.blood_group or "Unknown",
            "known_history": patient.medical_history_summary or "None documented",
            "allergies": patient.emergency_contact or "None documented"
        }

        # 2. Recent Vitals
        recent_encounters = db.query(Encounter).filter(
            Encounter.patient_id == patient_id
        ).order_by(Encounter.created_at.desc()).limit(5).all()

        vitals_list = []
        for enc in recent_encounters:
            for v in enc.vitals:
                vitals_list.append({
                    "date": str(v.recorded_at or v.created_at),
                    "bp": f"{v.blood_pressure_systolic}/{v.blood_pressure_diastolic} mmHg" if v.blood_pressure_systolic else "N/A",
                    "heart_rate": f"{v.heart_rate} bpm" if v.heart_rate else "N/A",
                    "resp_rate": f"{v.respiratory_rate} /min" if v.respiratory_rate else "N/A",
                    "spo2": f"{v.oxygen_saturation}%" if v.oxygen_saturation else "N/A",
                    "temp": f"{v.temperature_celsius}°C" if v.temperature_celsius else "N/A"
                })

        # 3. Active Prescriptions
        prescriptions = db.query(Prescription).filter(
            Prescription.patient_id == patient_id
        ).order_by(Prescription.created_at.desc()).limit(10).all()
        meds = []
        for p in prescriptions:
            if isinstance(p.medications, list):
                for m in p.medications:
                    if isinstance(m, dict):
                        meds.append({"medication": m.get("name", "Unknown"), "dosage": m.get("dosage", ""), "frequency": m.get("frequency", "")})
                    else:
                        meds.append({"medication": str(m), "dosage": "", "frequency": ""})
            elif p.medication_name:
                meds.append({"medication": p.medication_name, "dosage": p.dosage, "frequency": p.frequency})

        # 4. Recent Lab Results
        lab_results = db.query(LabResult).filter(
            LabResult.patient_id == patient_id
        ).order_by(LabResult.created_at.desc()).limit(8).all()
        labs = [{
            "test": r.order_item.test_definition.name if r.order_item and r.order_item.test_definition else "Lab Test",
            "value": f"{r.value} {r.unit or ''}".strip(),
            "flag": r.abnormal_flag.value if r.abnormal_flag else "NORMAL"
        } for r in lab_results]

        # 5. Missing Documentation Detection
        missing_items = []
        if not patient.blood_group:
            missing_items.append("Blood group not recorded.")
        if not patient.medical_history_summary:
            missing_items.append("Past medical history summary not documented.")
        if not vitals_list:
            missing_items.append("No vital signs recorded in active encounters.")

        # Construct untrusted clinical context
        clinical_context = (
            f"Patient: {demographics['name']}, DOB: {demographics['dob']}, Gender: {demographics['gender']}\n"
            f"Known Conditions: {demographics['known_history']}\n"
            f"Recent Vitals: {vitals_list}\n"
            f"Active Medications: {meds}\n"
            f"Recent Labs: {labs}\n"
        )

        def generate_clinical_summary():
            vitals_summary = f"Latest vitals: BP {vitals_list[0]['bp']}, HR {vitals_list[0]['heart_rate']}, SpO2 {vitals_list[0]['spo2']}." if vitals_list else "No recent vitals documented."
            meds_summary = f"Active regimens: {', '.join(m['medication'] + ' ' + m['dosage'] for m in meds[:3])}." if meds else "No active prescriptions on record."
            labs_summary = f"Recent laboratory investigations: {', '.join(l['test'] + ' (' + l['value'] + ')' for l in labs[:3])}." if labs else "No recent laboratory findings."
            
            return (
                f"### Clinical Synthesis for {demographics['name']} (ID: {demographics['patient_number'] or demographics['patient_id']})\n\n"
                f"- **Baseline**: {demographics['gender']}, DOB {demographics['dob']}, Blood Group: {demographics['blood_group']}\n"
                f"- **History**: {demographics['known_history']}\n"
                f"- **Telemetry & Vitals**: {vitals_summary}\n"
                f"- **Pharmacotherapy**: {meds_summary}\n"
                f"- **Diagnostics**: {labs_summary}\n\n"
                f"**Missing Documentation**: {'; '.join(missing_items) if missing_items else 'All core intake parameters documented.'}\n\n"
                f"⚠️ *DRAFT CLINICAL SYNTHESIS — Requires qualified clinician verification prior to clinical decision-making.*"
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=clinician,
            feature_name="unified_clinical_assistant",
            system_instruction=(
                "You are MediCore AI's Clinical Assistant. Synthesize the provided medical records concisely for the attending physician. "
                "Highlight key conditions, abnormal findings, active medications, and missing documentation. "
                "Do not invent facts not present in the record. Label your output as a clinician draft."
            ),
            user_prompt=f"Please synthesize the medical record for patient {demographics['name']}.",
            untrusted_clinical_context=clinical_context,
            deterministic_fallback_fn=generate_clinical_summary
        )

        return {
            "patient": demographics,
            "synthesis": ai_res["data"],
            "missing_documentation": missing_items,
            "vitals_count": len(vitals_list),
            "medications_count": len(meds),
            "labs_count": len(labs),
            "is_ai_draft": True,
            "disclaimer": "AI-generated clinical draft. Clinician must verify all observations against primary EHR source."
        }


clinical_assistant_service = ClinicalAssistantService()
