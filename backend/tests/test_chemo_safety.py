"""
Unit tests for Chemotherapy Safety, BSA calculation, and Dual-Nurse verification.
"""

import pytest
from app.services.chemo_safety_service import (
    ChemotherapySafetyEngine, HighAlertVerificationStatus
)

def test_bsa_mosteller_calculation():
    # 175 cm, 70 kg -> sqrt((175 * 70) / 3600) = sqrt(3.40277) ≈ 1.84 m²
    bsa = ChemotherapySafetyEngine.calculate_bsa_mosteller(height_cm=175.0, weight_kg=70.0)
    assert bsa == 1.84

def test_chemo_dose_calculation_safe():
    res = ChemotherapySafetyEngine.calculate_chemo_dose(
        height_cm=170.0,
        weight_kg=65.0,
        dose_per_m2_mg=60.0,
        drug_name="Doxorubicin",
        prior_cumulative_dose_mg=100.0
    )
    assert res["calculated_bsa_m2"] == 1.75
    assert res["calculated_total_dose_mg"] == 105.0
    assert res["is_blocked_by_lifetime_limit"] is False

def test_doxorubicin_cumulative_lifetime_limit_breach():
    # Patient with high prior cumulative dose of Doxorubicin (450 mg/m² max)
    # BSA = 1.84 -> max lifetime = 1.84 * 450 = 828 mg
    # Prior = 800 mg, new dose = 60 * 1.84 = 110.4 mg -> Total = 910.4 mg (EXCEEDS 828 mg)
    res = ChemotherapySafetyEngine.calculate_chemo_dose(
        height_cm=175.0,
        weight_kg=70.0,
        dose_per_m2_mg=60.0,
        drug_name="Doxorubicin",
        prior_cumulative_dose_mg=800.0
    )
    assert res["is_blocked_by_lifetime_limit"] is True
    assert res["lifetime_toxicity_alert"] is not None
    assert "cardiomyopathy" in res["lifetime_toxicity_alert"]["toxicity_warning"]

def test_dual_nursing_signoff_approved():
    res = ChemotherapySafetyEngine.verify_dual_nursing_signoff(
        calculated_dose_mg=100.0,
        prepared_dose_mg=101.5,
        nurse_1_id=10,
        nurse_2_id=12
    )
    assert res["status"] == HighAlertVerificationStatus.APPROVED.value
    assert res["variance_pct"] == 1.5

def test_dual_nursing_signoff_same_nurse_rejected():
    res = ChemotherapySafetyEngine.verify_dual_nursing_signoff(
        calculated_dose_mg=100.0,
        prepared_dose_mg=100.0,
        nurse_1_id=10,
        nurse_2_id=10  # Same nurse
    )
    assert res["status"] == "REJECTED"
    assert "two distinct licensed nurses" in res["message"]

def test_dual_nursing_signoff_variance_exceeded():
    # Prepared dose 115mg vs 100mg (15% variance > 5% allowed)
    res = ChemotherapySafetyEngine.verify_dual_nursing_signoff(
        calculated_dose_mg=100.0,
        prepared_dose_mg=115.0,
        nurse_1_id=10,
        nurse_2_id=12
    )
    assert res["status"] == HighAlertVerificationStatus.VARIANCE_EXCEEDED.value
    assert res["variance_pct"] == 15.0
