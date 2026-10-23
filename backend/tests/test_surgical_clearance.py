import pytest
from app.services.surgical_clearance_service import (
    SurgicalClearanceService,
    PreOpClearanceRequest
)

def test_rcri_class_1_low_risk():
    # 0 risk factors -> Class I
    req = PreOpClearanceRequest(
        patient_id="surg-001",
        procedure_name="Laparoscopic Cholecystectomy",
        is_high_risk_surgery=False,
        has_ischemic_heart_disease=False,
        has_congestive_heart_failure=False,
        has_cerebrovascular_disease=False,
        is_insulin_dependent_diabetic=False,
        serum_creatinine_mg_dl=0.9,
        functional_capacity_mets=6.0,
        asa_class=1
    )
    result = SurgicalClearanceService.evaluate_preop_risk(req)
    assert result["rcri_score"] == 0
    assert result["rcri_class"] == "Class I"
    assert result["clearance_status"] == "CLEARED_FOR_SURGERY"
    assert "ASA I: Normal healthy patient" in result["asa_classification"]

def test_rcri_class_4_high_risk():
    # High risk surgery (1) + HF (1) + Insulin (1) + Creatinine 2.4 (1) = 4 points -> Class IV
    req = PreOpClearanceRequest(
        patient_id="surg-002",
        procedure_name="Open Abdominal Aortic Aneurysm Repair",
        is_high_risk_surgery=True,
        has_ischemic_heart_disease=False,
        has_congestive_heart_failure=True,
        has_cerebrovascular_disease=False,
        is_insulin_dependent_diabetic=True,
        serum_creatinine_mg_dl=2.4,
        functional_capacity_mets=2.5,
        asa_class=4,
        is_emergency_surgery=True
    )
    result = SurgicalClearanceService.evaluate_preop_risk(req)
    assert result["rcri_score"] == 4
    assert result["rcri_class"] == "Class IV"
    assert result["cardiac_risk_level"] == "HIGH_CRITICAL_RISK"
    assert result["clearance_status"] == "HIGH_RISK_MULTIDISCIPLINARY_REQUIRED"
    assert "Emergency Modifier: E" in result["asa_classification"]
    assert "Poor Functional Capacity" in result["functional_capacity"]
    assert len(result["identified_risk_factors"]) == 4
