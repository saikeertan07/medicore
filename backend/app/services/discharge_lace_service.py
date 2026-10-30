"""
Automated Discharge Summary & LACE Index Readmission Risk Prediction Service.
Implements:
1. LACE Index scoring for 30-day hospital readmission risk:
   - L: Length of stay
   - A: Acuity of admission
   - C: Comorbidity (Charlson index)
   - E: Emergency department visits in past 6 months
2. Automated Discharge Summary Generation & Transition Care Planning.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class LACEAssessmentInput(BaseModel):
    patient_id: str
    length_of_stay_days: int = Field(..., ge=0, description="Inpatient stay duration in days")
    is_acute_admission: bool = Field(True, description="True if admitted via Emergency/Acute, False if Elective")
    charlson_comorbidity_score: int = Field(..., ge=0, description="Charlson Comorbidity Index score")
    ed_visits_past_6_months: int = Field(..., ge=0, description="ED visits in the preceding 6 months")

class DischargeSummaryInput(BaseModel):
    patient_id: str
    patient_name: str
    admission_date: str
    discharge_date: str
    primary_diagnosis: str
    secondary_diagnoses: List[str] = []
    hospital_course_summary: str
    discharge_medications: List[Dict[str, str]]
    follow_up_instructions: List[str]
    lace_input: Optional[LACEAssessmentInput] = None

class DischargeLACEService:
    CHARLSON_COMORBIDITY_WEIGHTS: Dict[str, int] = {
        "myocardial_infarction": 1,
        "congestive_heart_failure": 1,
        "peripheral_vascular_disease": 1,
        "cerebrovascular_disease": 1,
        "dementia": 1,
        "chronic_pulmonary_disease": 1,
        "connective_tissue_disease": 1,
        "peptic_ulcer_disease": 1,
        "mild_liver_disease": 1,
        "diabetes_uncomplicated": 1,
        "diabetes_end_organ_damage": 2,
        "hemiplegia": 2,
        "moderate_to_severe_renal_disease": 2,
        "solid_tumor": 2,
        "leukemia": 2,
        "lymphoma": 2,
        "moderate_to_severe_liver_disease": 3,
        "metastatic_solid_tumor": 6,
        "aids_hiv": 6
    }

    @classmethod
    def calculate_charlson_comorbidity_index(cls, conditions: List[str]) -> Dict[str, Any]:
        """Calculates authoritative Charlson Comorbidity Index with clinical hierarchy deduplication."""
        matched_dict = {}
        normalized_conditions = [c.lower().strip().replace(" ", "_").replace("-", "_") for c in conditions]

        for condition_key, weight in cls.CHARLSON_COMORBIDITY_WEIGHTS.items():
            if any(condition_key == nc or condition_key in nc for nc in normalized_conditions):
                matched_dict[condition_key] = weight

        # Hierarchy exclusions:
        # 1. Metastatic solid tumor (6) supersedes localized solid tumor (2)
        if "metastatic_solid_tumor" in matched_dict and "solid_tumor" in matched_dict:
            del matched_dict["solid_tumor"]

        # 2. Severe liver disease (3) supersedes mild liver disease (1)
        if "moderate_to_severe_liver_disease" in matched_dict and "mild_liver_disease" in matched_dict:
            del matched_dict["mild_liver_disease"]

        # 3. Diabetes with end organ damage (2) supersedes uncomplicated diabetes (1)
        if "diabetes_end_organ_damage" in matched_dict and "diabetes_uncomplicated" in matched_dict:
            del matched_dict["diabetes_uncomplicated"]

        total_score = sum(matched_dict.values())
        matched_conditions = [{"condition": k, "weight": v} for k, v in matched_dict.items()]

        return {
            "charlson_score": total_score,
            "matched_conditions": matched_conditions,
            "condition_count": len(matched_conditions)
        }

    @classmethod
    def calculate_lace_score(cls, data: LACEAssessmentInput) -> Dict[str, Any]:
        # L - Length of stay
        los = data.length_of_stay_days
        if los < 1:
            l_points = 0
        elif los == 1:
            l_points = 1
        elif los == 2:
            l_points = 2
        elif los == 3:
            l_points = 3
        elif 4 <= los <= 6:
            l_points = 4
        elif 7 <= los <= 13:
            l_points = 5
        else: # >= 14
            l_points = 7

        # A - Acuity of admission
        a_points = 3 if data.is_acute_admission else 0

        # C - Charlson Comorbidity Index
        cci = data.charlson_comorbidity_score
        if cci == 0:
            c_points = 0
        elif cci == 1:
            c_points = 1
        elif cci == 2:
            c_points = 2
        elif cci == 3:
            c_points = 3
        else: # >= 4
            c_points = 5

        # E - Emergency department visits in prior 6 months
        ed = data.ed_visits_past_6_months
        if ed == 0:
            e_points = 0
        elif ed == 1:
            e_points = 1
        elif ed == 2:
            e_points = 2
        elif ed == 3:
            e_points = 3
        else: # >= 4
            e_points = 4

        total_lace = l_points + a_points + c_points + e_points

        if total_lace >= 10:
            risk_category = "HIGH_RISK"
            estimated_readmission_rate = "23% - 40%"
            care_plan = [
                "Schedule primary care follow-up within 3-5 days post-discharge.",
                "Assign designated Nurse Transition Navigator for 48-hour phone outreach.",
                "Conduct formal pharmacist medication reconciliation prior to discharge.",
                "Assess eligibility for Home Health Nursing and outpatient physical therapy."
            ]
        elif 5 <= total_lace <= 9:
            risk_category = "MODERATE_RISK"
            estimated_readmission_rate = "9% - 15%"
            care_plan = [
                "Schedule outpatient follow-up appointment within 7-10 days.",
                "Post-discharge welfare telephone check-in at 72 hours.",
                "Provide detailed red-flag symptom warning sheet."
            ]
        else:
            risk_category = "LOW_RISK"
            estimated_readmission_rate = "< 5%"
            care_plan = [
                "Routine follow-up with PCP within 14-30 days as clinically indicated.",
                "Standard printed discharge instructions and return precautions."
            ]

        return {
            "patient_id": data.patient_id,
            "total_lace_score": total_lace,
            "max_lace_score": 19,
            "risk_category": risk_category,
            "estimated_30day_readmission_rate": estimated_readmission_rate,
            "high_risk_transition_flag": total_lace >= 10,
            "complex_case_management_referral_mandate": total_lace >= 14,
            "component_breakdown": {
                "length_of_stay_points": l_points,
                "acuity_points": a_points,
                "comorbidity_points": c_points,
                "prior_ed_visits_points": e_points
            },
            "transition_care_interventions": care_plan
        }

    @classmethod
    def generate_discharge_packet(cls, summary: DischargeSummaryInput) -> Dict[str, Any]:
        lace_analysis = None
        if summary.lace_input:
            lace_analysis = cls.calculate_lace_score(summary.lace_input)

        red_flag_warnings = [
            "Sudden severe shortness of breath or persistent chest discomfort",
            "Fever > 101°F (38.3°C) or uncontrolled rigors / chills",
            "Inability to tolerate oral fluids or medications due to intractable vomiting",
            "Confusion, acute weakness, speech slurring, or sudden numbness",
            "Excessive bleeding or discharge from surgical incisions or wounds"
        ]

        return {
            "document_type": "OFFICIAL_HOSPITAL_DISCHARGE_SUMMARY",
            "patient_id": summary.patient_id,
            "patient_name": summary.patient_name,
            "admission_date": summary.admission_date,
            "discharge_date": summary.discharge_date,
            "primary_diagnosis": summary.primary_diagnosis,
            "secondary_diagnoses": summary.secondary_diagnoses,
            "clinical_course": summary.hospital_course_summary,
            "discharge_medications": summary.discharge_medications,
            "follow_up_instructions": summary.follow_up_instructions,
            "lace_risk_assessment": lace_analysis,
            "emergency_return_precautions": red_flag_warnings,
            "transition_care_status": "PENDING_DISMISSAL_SIGN_OFF"
        }
