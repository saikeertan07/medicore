"""
Surgical Pre-Operative Clearance & Cardiac Risk Engine.
Implements:
1. Revised Cardiac Risk Index (Lee's RCRI) for predicting Major Adverse Cardiac Events (MACE).
2. ASA Physical Status Classification (ASA I - VI + Emergency modifier).
3. Functional Capacity Assessment (Metabolic Equivalents of Task - METs).
4. Evidence-based perioperative cardiac risk stratification and clearance recommendations.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class PreOpClearanceRequest(BaseModel):
    patient_id: str
    procedure_name: str
    is_high_risk_surgery: bool = Field(False, description="Intraperitoneal, intrathoracic, or suprainguinal vascular surgery")
    has_ischemic_heart_disease: bool = Field(False, description="History of MI, positive stress test, angina, prior PCI or CABG")
    has_congestive_heart_failure: bool = Field(False, description="History of HF, pulmonary edema, paroxysmal nocturnal dyspnea, or EF < 40%")
    has_cerebrovascular_disease: bool = Field(False, description="History of TIA or stroke")
    is_insulin_dependent_diabetic: bool = Field(False, description="Pre-operative insulin therapy")
    serum_creatinine_mg_dl: float = Field(..., ge=0.1, le=25.0, description="Pre-op baseline serum creatinine")
    functional_capacity_mets: Optional[float] = Field(None, description="Metabolic equivalents: <4 = poor, >=4 = adequate")
    asa_class: Optional[int] = Field(None, ge=1, le=6, description="ASA Physical Status Classification I to VI")
    is_emergency_surgery: bool = Field(False, description="Emergency surgical procedure modifier")

class SurgicalClearanceService:
    @classmethod
    def evaluate_preop_risk(cls, req: PreOpClearanceRequest) -> Dict[str, Any]:
        rcri_points = 0
        positive_criteria = []

        if req.is_high_risk_surgery:
            rcri_points += 1
            positive_criteria.append("High-risk surgery (intraperitoneal, intrathoracic, or suprainguinal vascular)")

        if req.has_ischemic_heart_disease:
            rcri_points += 1
            positive_criteria.append("History of ischemic heart disease")

        if req.has_congestive_heart_failure:
            rcri_points += 1
            positive_criteria.append("History of congestive heart failure")

        if req.has_cerebrovascular_disease:
            rcri_points += 1
            positive_criteria.append("History of cerebrovascular disease / prior TIA/stroke")

        if req.is_insulin_dependent_diabetic:
            rcri_points += 1
            positive_criteria.append("Preoperative insulin-dependent diabetes")

        if req.serum_creatinine_mg_dl > 2.0:
            rcri_points += 1
            positive_criteria.append(f"Preoperative renal insufficiency (Cr: {req.serum_creatinine_mg_dl} > 2.0 mg/dL)")

        # RCRI Stratification
        if rcri_points == 0:
            rcri_class = "Class I"
            mace_rate = "0.4% - 0.5%"
            risk_level = "LOW_RISK"
            clearance_status = "CLEARED_FOR_SURGERY"
            recommendations = [
                "Cleared for non-cardiac surgery without routine further cardiac diagnostics.",
                "Maintain baseline medications as per standard institutional fasting/surgical protocol."
            ]
        elif rcri_points == 1:
            rcri_class = "Class II"
            mace_rate = "0.9% - 1.0%"
            risk_level = "MODERATE_LOW_RISK"
            clearance_status = "CLEARED_WITH_MONITORING"
            recommendations = [
                "Preoperative baseline 12-lead ECG indicated.",
                "Ensure intraoperative hemodynamic stability and adequate fluid management.",
                "Continue beta-blockers/statins if already prescribed chronic therapy."
            ]
        elif rcri_points == 2:
            rcri_class = "Class III"
            mace_rate = "4.0% - 6.6%"
            risk_level = "ELEVATED_RISK"
            clearance_status = "CONDITIONAL_CLEARANCE_CARDIOLOGY_REVIEW"
            recommendations = [
                "Preoperative Cardiology consultation recommended.",
                "Evaluate functional status (METs). If functional capacity < 4 METs, consider pre-op stress echo.",
                "Plan post-operative continuous ECG telemetry and surveillance troponin screening at 24 and 48 hours."
            ]
        else: # >= 3
            rcri_class = "Class IV"
            mace_rate = "> 11.0%"
            risk_level = "HIGH_CRITICAL_RISK"
            clearance_status = "HIGH_RISK_MULTIDISCIPLINARY_REQUIRED"
            recommendations = [
                "URGENT Multidisciplinary preoperative conference (Anesthesiology, Cardiology, Surgery).",
                "Formal preoperative transthoracic echocardiogram (TTE) to evaluate LV ejection fraction and valvular disease.",
                "Mandatory post-op ICU or Step-down telemetry bed reservation.",
                "Daily serial troponins and 12-lead ECGs for at least 48 to 72 hours post-op."
            ]

        # ASA text interpretation
        asa_descriptions = {
            1: "ASA I: Normal healthy patient",
            2: "ASA II: Patient with mild systemic disease (no functional limitation)",
            3: "ASA III: Patient with severe systemic disease (substantive functional limitation)",
            4: "ASA IV: Patient with severe systemic disease that is a constant threat to life",
            5: "ASA V: Moribund patient not expected to survive without the operation",
            6: "ASA VI: Declared brain-dead patient whose organs are being removed for donor purposes"
        }
        asa_label = None
        if req.asa_class:
            asa_label = asa_descriptions.get(req.asa_class, f"ASA {req.asa_class}")
            if req.is_emergency_surgery:
                asa_label += " (Emergency Modifier: E)"

        mets_status = None
        if req.functional_capacity_mets is not None:
            if req.functional_capacity_mets < 4.0:
                mets_status = "Poor Functional Capacity (< 4 METs) - elevated perioperative risk"
            else:
                mets_status = "Adequate Functional Capacity (>= 4 METs)"

        return {
            "patient_id": req.patient_id,
            "procedure_name": req.procedure_name,
            "rcri_score": rcri_points,
            "rcri_class": rcri_class,
            "cardiac_risk_level": risk_level,
            "estimated_mace_incidence": mace_rate,
            "clearance_status": clearance_status,
            "identified_risk_factors": positive_criteria,
            "asa_classification": asa_label,
            "functional_capacity": mets_status,
            "clinical_recommendations": recommendations
        }
