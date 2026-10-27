import pytest
from app.services.clinical_decision_support_service import (
    ClinicalDecisionSupportService,
    clinical_decision_support_service,
    KNOWN_RENAL_DOSE_ADJUSTMENTS,
    KNOWN_DRUG_INTERACTIONS,
    ALLERGY_CROSS_REACTIVITY
)
from app.ai.tools.nurse_tools import evaluate_sepsis_risk
from app.ai.tools.doctor_tools import (
    evaluate_patient_cds_safety,
    evaluate_patient_renal_safety
)
from app.models.models import User, UserRole, Patient, Doctor


def test_cockcroft_gault_creatinine_clearance_calculation():
    """
    Validates Cockcroft-Gault CrCl equation:
    CrCl = [(140 - Age) * Weight(kg)] / [72 * Creatinine(mg/dL)] (* 0.85 if female)
    """
    # 60yo male, 70kg, Cr 1.0 mg/dL: [(140-60)*70] / (72*1.0) = 5600 / 72 = 77.8 mL/min
    crcl_male = ClinicalDecisionSupportService.calculate_creatinine_clearance(
        age=60, weight_kg=70.0, serum_creatinine=1.0, is_female=False
    )
    assert crcl_male == 77.8

    # 60yo female, 70kg, Cr 1.0 mg/dL: 77.78 * 0.85 = 66.1 mL/min
    crcl_female = ClinicalDecisionSupportService.calculate_creatinine_clearance(
        age=60, weight_kg=70.0, serum_creatinine=1.0, is_female=True
    )
    assert crcl_female == 66.1

    # Renal failure case: 75yo female, 50kg, Cr 2.5 mg/dL:
    # [(140-75)*50] / (72*2.5) = 3250 / 180 = 18.06 * 0.85 = 15.35 -> 15.3 mL/min
    crcl_severe_renal = ClinicalDecisionSupportService.calculate_creatinine_clearance(
        age=75, weight_kg=50.0, serum_creatinine=2.5, is_female=True
    )
    assert crcl_severe_renal == 15.3

    # Boundary conditions
    assert ClinicalDecisionSupportService.calculate_creatinine_clearance(0, 70.0, 1.0) == 0.0
    assert ClinicalDecisionSupportService.calculate_creatinine_clearance(60, 0.0, 1.0) == 0.0
    assert ClinicalDecisionSupportService.calculate_creatinine_clearance(60, 70.0, 0.0) == 0.0


def test_renal_dose_adjustment_rules():
    """
    Verifies that renal dosing alert definitions contain expected high-risk therapeutic classes.
    """
    drug_keys = {rule["drug_key"] for rule in KNOWN_RENAL_DOSE_ADJUSTMENTS}
    assert "metformin" in drug_keys
    assert "enoxaparin" in drug_keys
    assert "cefepime" in drug_keys
    assert "vancomycin" in drug_keys
    assert "ciprofloxacin" in drug_keys

    # Metformin critical contraindication threshold must be 30 mL/min
    metformin_crit = next(
        r for r in KNOWN_RENAL_DOSE_ADJUSTMENTS
        if r["drug_key"] == "metformin" and r["threshold_crcl"] == 30.0
    )
    assert metformin_crit["severity"] == "CRITICAL"
    assert "lactic acidosis" in metformin_crit["description"].lower()


def test_nurse_sepsis_risk_evaluation_tool():
    """
    Tests evaluate_sepsis_risk tool wrapper for qSOFA and SIRS calculation.
    """
    res = evaluate_sepsis_risk(
        patient_id=101,
        systolic_bp=90,      # Hypotension: SBP <= 100 (+1)
        heart_rate=115,     # SIRS: HR > 90
        respiration_rate=24, # Tachypnea: RR >= 22 (+1)
        temperature=38.8,   # Fever: Temp > 38.0
        altered_mentation=True, # AMS: GCS altered (+1)
        suspected_infection_source="Pulmonary / Pneumonia",
        serum_lactate=3.2   # Elevated lactate > 2.0
    )

    assert "qsofa" in res
    assert res["qsofa"]["qsofa_score"] == 3
    assert res["qsofa"]["is_positive"] is True
    assert res["risk_level"] in ["CRITICAL_SEPSIS_ALERT", "SEPTIC_SHOCK"]
    assert res["requires_emergency_code_sepsis"] is True
    assert "one_hour_sepsis_bundle" in res
    assert len(res["one_hour_sepsis_bundle"]) > 0


def test_doctor_cds_tool_authorization_denial(db_session):
    """
    Verifies that doctor CDS tools reject unauthorized physicians or unassigned encounters.
    """
    # Create doctor without patient relationship
    doctor_user = User(
        email="unauth_doc@medicore.org",
        full_name="Dr. Unassigned Physician",
        hashed_password="hashed_pass_test",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db_session.add(doctor_user)
    db_session.commit()

    res = evaluate_patient_cds_safety(
        db=db_session,
        current_user=doctor_user,
        patient_id=99999
    )
    assert res["authorized"] is False
    assert "Access denied" in res["error"]
