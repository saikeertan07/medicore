import pytest
from app.services.tpn_nutrition_service import (
    TPNNutritionService,
    TPNOrderRequest
)

def test_tpn_standard_order():
    # 70 kg, 175 cm, 45 yo male, uncomplicated inpatient, 2000 mL volume
    req = TPNOrderRequest(
        patient_id="tpn-001",
        weight_kg=70.0,
        height_cm=175.0,
        age_years=45,
        gender="male",
        clinical_condition="uncomplicated_inpatient",
        target_fluid_volume_ml=2100.0,
        calcium_mEq=10.0,
        phosphate_mmol=25.0
    )
    result = TPNNutritionService.calculate_tpn_prescription(req)
    assert result["basal_energy_expenditure_kcal"] > 1400
    assert result["total_daily_caloric_target_kcal"] > 1500
    assert result["macronutrients"]["amino_acids"]["grams"] == 70.0 # 1.0 g/kg
    # Ca 10 / 2.1 = 4.76 mEq/L, PO4 25 / 2.1 = 11.9 mmol/L -> sum ~16.7 < 35 -> SAFE
    assert result["calcium_phosphate_compatibility"]["precipitation_status"] == "SAFE"
    assert len(result["safety_alerts"]) == 0

def test_tpn_calcium_phosphate_precipitation_alert():
    # Restricted fluid volume (1000 mL) with high calcium (25 mEq) and high phosphate (45 mmol) -> sum = 70 >= 35 -> CRITICAL
    req = TPNOrderRequest(
        patient_id="tpn-002",
        weight_kg=60.0,
        height_cm=160.0,
        age_years=55,
        gender="female",
        clinical_condition="critically_ill",
        target_fluid_volume_ml=1000.0,
        calcium_mEq=25.0,
        phosphate_mmol=45.0
    )
    result = TPNNutritionService.calculate_tpn_prescription(req)
    assert result["calcium_phosphate_compatibility"]["precipitation_status"] == "CRITICAL_DANGER_PRECIPITATION_RISK"
    assert len(result["safety_alerts"]) >= 1
    assert "precipitation" in result["safety_alerts"][0].lower()
