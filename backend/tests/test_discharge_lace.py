import pytest
from app.services.discharge_lace_service import (
    DischargeLACEService,
    LACEAssessmentInput,
    DischargeSummaryInput
)

def test_lace_low_risk():
    # LOS = 1 day (1 pt), Elective (0 pt), Charlson = 0 (0 pt), ED visits = 0 (0 pt) -> Total = 1 pt (Low)
    data = LACEAssessmentInput(
        patient_id="pt-101",
        length_of_stay_days=1,
        is_acute_admission=False,
        charlson_comorbidity_score=0,
        ed_visits_past_6_months=0
    )
    result = DischargeLACEService.calculate_lace_score(data)
    assert result["total_lace_score"] == 1
    assert result["risk_category"] == "LOW_RISK"
    assert "< 5%" in result["estimated_30day_readmission_rate"]

def test_lace_high_risk():
    # LOS = 8 days (5 pt), Acute (3 pt), Charlson = 3 (3 pt), ED visits = 2 (2 pt) -> Total = 13 pt (High)
    data = LACEAssessmentInput(
        patient_id="pt-102",
        length_of_stay_days=8,
        is_acute_admission=True,
        charlson_comorbidity_score=3,
        ed_visits_past_6_months=2
    )
    result = DischargeLACEService.calculate_lace_score(data)
    assert result["total_lace_score"] == 13
    assert result["risk_category"] == "HIGH_RISK"
    assert "Nurse Transition Navigator" in result["transition_care_interventions"][1]

def test_discharge_summary_generation():
    lace_in = LACEAssessmentInput(
        patient_id="pt-103",
        length_of_stay_days=3,
        is_acute_admission=True,
        charlson_comorbidity_score=1,
        ed_visits_past_6_months=0
    )
    summary_in = DischargeSummaryInput(
        patient_id="pt-103",
        patient_name="John Doe",
        admission_date="2026-10-10",
        discharge_date="2026-10-13",
        primary_diagnosis="Community Acquired Pneumonia",
        secondary_diagnoses=["Hypertension"],
        hospital_course_summary="Patient completed 3 days of IV Ceftriaxone with complete resolution of fever and leukocytosis.",
        discharge_medications=[
            {"drug": "Amoxicillin/Clavulanate", "dosage": "875/125 mg PO BID", "duration": "5 days"}
        ],
        follow_up_instructions=["Follow up with Dr. Smith in 1 week"],
        lace_input=lace_in
    )
    packet = DischargeLACEService.generate_discharge_packet(summary_in)
    assert packet["document_type"] == "OFFICIAL_HOSPITAL_DISCHARGE_SUMMARY"
    assert packet["lace_risk_assessment"]["total_lace_score"] == 7 # LOS 3(3) + Acute(3) + Charlson 1(1) + ED 0 = 7
    assert packet["lace_risk_assessment"]["risk_category"] == "MODERATE_RISK"
    assert len(packet["emergency_return_precautions"]) >= 3
