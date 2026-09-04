"""
Feature 8 — AI Pharmacy Safety Assistant Service
Performs medication reconciliation, duplicate therapy checks, and inventory demand alerts.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Prescription, 
    PharmacySafetyAlert, InventoryItem, InventoryStatus
)
from app.ai.gateway import ai_gateway

# Duplicate Therapeutic Classes
THERAPEUTIC_DUPLICATION_CLASSES = {
    "nsaid": ["ibuprofen", "naproxen", "meloxicam", "ketorolac", "diclofenac", "celecoxib", "aspirin"],
    "beta_blocker": ["metoprolol", "atenolol", "propranolol", "carvedilol", "bisoprolol"],
    "ace_inhibitor": ["lisinopril", "enalapril", "ramipril", "captopril", "benazepril"],
    "arb": ["losartan", "valsartan", "irbesartan", "olmesartan", "candesartan"],
    "statin": ["atorvastatin", "simvastatin", "rosuvastatin", "pravastatin"],
    "benzo": ["lorazepam", "alprazolam", "clonazepam", "diazepam", "temazepam"],
    "ppi": ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole"]
}


class PharmacySafetyService:
    def evaluate_prescriptions_safety(
        self,
        db: Session,
        clinician: User,
        patient_id: int
    ) -> Dict[str, Any]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        prescriptions = db.query(Prescription).filter(
            Prescription.patient_id == patient_id
        ).all()

        alerts = []
        med_entries = []
        for p in prescriptions:
            if isinstance(p.medications, list):
                for m in p.medications:
                    name = m.get("name", "") if isinstance(m, dict) else str(m)
                    if name:
                        med_entries.append({"name": name, "prescription": p})
            elif p.medication_name:
                med_entries.append({"name": p.medication_name, "prescription": p})

        # 1. Detect Duplicate Therapeutic Classes
        for class_name, drugs in THERAPEUTIC_DUPLICATION_CLASSES.items():
            matched = [entry for entry in med_entries if any(d in entry["name"].lower() for d in drugs)]
            if len(matched) > 1:
                names = ", ".join(m["name"] for m in matched)
                alert_obj = PharmacySafetyAlert(
                    patient_id=patient_id,
                    prescription_id=matched[0]["prescription"].id,
                    alert_type="DUPLICATE_THERAPY",
                    severity="HIGH",
                    medication_names=names,
                    description=f"Duplicate therapeutic class ({class_name.upper()}): Patient is concurrently prescribed {names}. Risks cumulative toxicity."
                )
                db.add(alert_obj)
                alerts.append({
                    "alert_type": "DUPLICATE_THERAPY",
                    "severity": "HIGH",
                    "medications": names,
                    "description": alert_obj.description
                })

        db.commit()

        # 2. Inventory Stock Risk Alerts
        low_stock_items = db.query(InventoryItem).filter(
            InventoryItem.status.in_([InventoryStatus.LOW_STOCK, InventoryStatus.CRITICAL])
        ).all()
        stock_alerts = [{
            "item_name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
            "status": item.status.value,
            "reorder_level": item.reorder_level
        } for item in low_stock_items]

        def generate_pharmacy_summary():
            if not alerts and not stock_alerts:
                return "Medication reconciliation complete: No duplicate therapies or critical inventory shortages detected."
            summary_parts = []
            if alerts:
                summary_parts.append(f"⚠️ **Duplicate Therapy Alerts**: Found {len(alerts)} therapeutic overlaps requiring physician de-escalation.")
            if stock_alerts:
                summary_parts.append(f"📦 **Pharmacy Inventory Warnings**: {len(stock_alerts)} items are currently below reorder thresholds.")
            return "\n\n".join(summary_parts)

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=clinician,
            feature_name="pharmacy_safety_assistant",
            system_instruction=(
                "You are MediCore AI's Pharmacy Safety Assistant. Review medication duplicate therapy and inventory alerts. "
                "Highlight patient safety risks and inventory supply considerations concisely."
            ),
            user_prompt=f"Review pharmacy safety for patient {patient.display_name}.",
            untrusted_clinical_context=f"Alerts: {alerts}, Stock: {stock_alerts}",
            deterministic_fallback_fn=generate_pharmacy_summary
        )

        return {
            "patient_id": patient_id,
            "active_prescriptions_count": len(prescriptions),
            "duplicate_therapy_alerts": alerts,
            "inventory_stock_alerts": stock_alerts,
            "synthesis": ai_res["data"],
            "disclaimer": "All pharmacy safety alerts require clinical verification before altering prescriptions or dispensing."
        }


pharmacy_safety_service = PharmacySafetyService()
