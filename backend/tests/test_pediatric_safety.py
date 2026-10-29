import pytest
from app.services.pediatric_safety_service import (
    PediatricSafetyService,
    APGARAssessment,
    PediatricEmergencyRequest
)

def test_apgar_normal():
    # 2 for all -> 10
    assessment = APGARAssessment(
        time_minutes=1,
        appearance=2,
        pulse=2,
        grimace=2,
        activity=2,
        respiration=2
    )
    result = PediatricSafetyService.calculate_apgar(assessment)
    assert result["apgar_score"] == 10
    assert result["urgency"] == "ROUTINE"
    assert "Routine newborn care" in result["clinical_recommendations"][0]

def test_apgar_depressed():
    # 1+0+1+0+1 = 3 -> Critical
    assessment = APGARAssessment(
        time_minutes=5,
        appearance=1,
        pulse=0,
        grimace=1,
        activity=0,
        respiration=1
    )
    result = PediatricSafetyService.calculate_apgar(assessment)
    assert result["apgar_score"] == 3
    assert result["urgency"] == "STAT_CRITICAL"
    assert "IMMEDIATE RESUSCITATION REQUIRED" in result["clinical_recommendations"][0]

def test_broselow_length_mapping():
    # Length 72 cm should map to Red Zone (8.5 kg)
    req = PediatricEmergencyRequest(
        patient_id="ped-001",
        length_cm=72.0
    )
    result = PediatricSafetyService.calculate_pediatric_dosing(req)
    assert result["broselow_tape_zone"] == "Red"
    assert result["calculated_weight_kg"] == 8.5
    # Epi dose = min(0.01 * 8.5, 1.0) = 0.085 mg
    assert result["emergency_medications"]["epinephrine_cardiac_arrest_iv_io"]["dose_mg"] == 0.085
    # Initial Defib = 2 * 8.5 = 17 J
    assert "17 Joules" in result["electrical_therapy"]["defibrillation_initial"]
    # ETT cuffed = 3.0
    assert result["airway_equipment"]["ett_cuffed_mm"] == 3.0

def test_broselow_explicit_weight():
    # Actual weight 20 kg -> Blue zone
    req = PediatricEmergencyRequest(
        patient_id="ped-002",
        actual_weight_kg=20.0
    )
    result = PediatricSafetyService.calculate_pediatric_dosing(req)
    assert result["calculated_weight_kg"] == 20.0
    # Defib 2 J/kg = 40 J, second = 80 J
    assert "40 Joules" in result["electrical_therapy"]["defibrillation_initial"]
    assert "80 Joules" in result["electrical_therapy"]["defibrillation_subsequent"]
    # Fluid bolus = 20 mL/kg = 400 mL
    assert result["fluid_resuscitation"]["bolus_volume_ml"] == 400

def test_pediatric_dextrose_hypoglycemia_resuscitation():
    # Infant < 10kg receives D10W (5 mL/kg)
    infant_req = PediatricEmergencyRequest(patient_id="ped-infant", actual_weight_kg=6.0)
    infant_res = PediatricSafetyService.calculate_pediatric_dosing(infant_req)
    dex_infant = infant_res["emergency_medications"]["dextrose_hypoglycemia_bolus"]
    assert "D10W" in dex_infant["solution"]
    assert dex_infant["volume_ml"] == 30.0  # 5 mL/kg * 6 kg = 30 mL

    # Child 20kg receives D25W (2 mL/kg)
    child_req = PediatricEmergencyRequest(patient_id="ped-child", actual_weight_kg=20.0)
    child_res = PediatricSafetyService.calculate_pediatric_dosing(child_req)
    dex_child = child_res["emergency_medications"]["dextrose_hypoglycemia_bolus"]
    assert "D25W" in dex_child["solution"]
    assert dex_child["volume_ml"] == 40.0  # 2 mL/kg * 20 kg = 40 mL

    # Adolescent 40kg receives D50W (1 mL/kg capped at 50 mL)
    adol_req = PediatricEmergencyRequest(patient_id="ped-adol", actual_weight_kg=40.0)
    adol_res = PediatricSafetyService.calculate_pediatric_dosing(adol_req)
    dex_adol = adol_res["emergency_medications"]["dextrose_hypoglycemia_bolus"]
    assert "D50W" in dex_adol["solution"]
    assert dex_adol["volume_ml"] == 40.0

