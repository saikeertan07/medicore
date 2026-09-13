"""
Anesthesia Pre-Evaluation & Difficult Airway Prediction Service.
Implements:
1. Mallampati Airway Classification (Class I through IV).
2. The LEMON Difficult Airway Assessment Method:
   - L: Look externally
   - E: Evaluate 3-3-2 Rule (interincisor, hyomental, thyroid-to-hyoid)
   - M: Mallampati score >= Class III
   - O: Obstruction / stridor / hematoma
   - N: Neck mobility limitation (c-spine precautions, ankylosis)
3. ASA Difficult Airway Algorithm equipment recommendations (Video Laryngoscopy, Bougie, Cricothyrotomy kit).
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AirwayEvaluationRequest(BaseModel):
    patient_id: str
    mallampati_class: int = Field(..., ge=1, le=4, description="Mallampati Class 1 to 4")
    look_abnormal_external: bool = Field(False, description="Facial trauma, severe micrognathia, prominent incisors, full beard")
    rule_3_3_2_met: bool = Field(True, description="True if mouth opens >=3 fingers, hyomental distance >=3 fingers, thyroid-to-hyoid >=2 fingers")
    has_airway_obstruction: bool = Field(False, description="Tumor, peritonsillar abscess, stridor, Ludwig's angina, neck hematoma")
    limited_neck_mobility: bool = Field(False, description="C-spine collar, cervical spine fusion, rheumatoid arthritis")
    prior_difficult_intubation_history: bool = Field(False, description="Patient or family history of difficult intubation or 'cannot intubate cannot oxygenate'")

class AnesthesiaAirwayService:
    @classmethod
    def evaluate_airway(cls, req: AirwayEvaluationRequest) -> Dict[str, Any]:
        lemon_score = 0
        risk_factors = []

        # L
        if req.look_abnormal_external:
            lemon_score += 1
            risk_factors.append("Look: Abnormal external facial/mandibular features or trauma")

        # E
        if not req.rule_3_3_2_met:
            lemon_score += 1
            risk_factors.append("Evaluate 3-3-2: Failed 3-3-2 anatomical distance criteria")

        # M
        if req.mallampati_class >= 3:
            lemon_score += 1
            risk_factors.append(f"Mallampati: Elevated class ({req.mallampati_class}) with obscured glottic visibility")

        # O
        if req.has_airway_obstruction:
            lemon_score += 1
            risk_factors.append("Obstruction: Upper airway pathology / mass / hematoma / stridor present")

        # N
        if req.limited_neck_mobility:
            lemon_score += 1
            risk_factors.append("Neck Mobility: Severe cervical spine restriction or trauma collar")

        # History flag
        if req.prior_difficult_intubation_history:
            risk_factors.append("Documented Prior Difficult Airway History")

        # Mallampati details
        mallampati_descriptions = {
            1: "Class I: Soft palate, uvula, fauces, pillars completely visible (Easy intubation expected)",
            2: "Class II: Soft palate, major portion of uvula, fauces visible",
            3: "Class III: Soft palate and base of uvula visible only (Difficult airway warning)",
            4: "Class IV: Only hard palate visible, soft palate completely obscured (Severe difficult intubation warning)"
        }

        # Airway Risk Stratification
        if lemon_score >= 3 or req.prior_difficult_intubation_history or req.mallampati_class == 4:
            airway_class = "CRITICAL_DIFFICULT_AIRWAY"
            risk_description = "High probability of difficult direct laryngoscopy and intubation."
            equipment_plan = [
                "Primary video laryngoscope (e.g. GlideScope / McGrath) at bedside.",
                "Endotracheal tube with pre-loaded flexible Bougie introducer.",
                "Supraglottic Airway (LMA Supreme / i-gel) verified ready for rescue ventilation.",
                "Prepare fiberoptic bronchoscope or awake intubation protocol.",
                "Emergency surgical cricothyrotomy kit immediately accessible at bedside.",
                "Second anesthesia attending / experienced airway specialist present at induction."
            ]
        elif lemon_score in [1, 2]:
            airway_class = "MODERATE_DIFFICULT_AIRWAY"
            risk_description = "Intermediate difficulty risk. Standard direct laryngoscopy may require secondary techniques."
            equipment_plan = [
                "Direct laryngoscope blade + Video laryngoscope on standby in OR.",
                "Stylet / Bougie immediately within reach.",
                "Appropriately sized Supraglottic Airway ready."
            ]
        else:
            airway_class = "ROUTINE_PREDICTED_NORMAL_AIRWAY"
            risk_description = "Normal airway parameters. Standard airway management indicated."
            equipment_plan = [
                "Standard direct or video laryngoscopy setup.",
                "Standard stylet and suction."
            ]

        return {
            "patient_id": req.patient_id,
            "lemon_score": lemon_score,
            "max_lemon_score": 5,
            "airway_risk_classification": airway_class,
            "risk_summary": risk_description,
            "mallampati_class": req.mallampati_class,
            "mallampati_description": mallampati_descriptions[req.mallampati_class],
            "identified_risk_criteria": risk_factors,
            "asa_airway_equipment_readiness": equipment_plan
        }
