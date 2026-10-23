"""
Unit tests for Blood Bank Crossmatch & Massive Transfusion Protocol.
"""

import pytest
from app.services.blood_bank_service import BloodBankEngine, BloodType

def test_rbc_compatibility_universal_donor():
    # O Negative is compatible with all recipient blood types
    for rec_type in BloodType:
        res = BloodBankEngine.check_rbc_compatibility(rec_type.value, "O_NEG")
        assert res["is_compatible"] is True
        assert res["action"] == "APPROVED_FOR_CROSSMATCH"

def test_incompatible_transfusion_blocked():
    # A Positive blood transfused to B Positive recipient is incompatible
    res = BloodBankEngine.check_rbc_compatibility("B_POS", "A_POS")
    assert res["is_compatible"] is False
    assert res["action"] == "CONTRAINDICATED_HEMOLYTIC_TRANSFUSION_RISK"
    assert "hemolytic transfusion reaction" in res["warning"]

def test_emergency_uncrossmatched_female_childbearing():
    res = BloodBankEngine.generate_emergency_uncrossmatched_release(patient_gender="female", patient_age=28)
    assert res["emergency_release"] is True
    assert res["recommended_blood_type"] == "O_NEG"
    assert "anti-D hemolytic disease" in res["rationale"]

def test_emergency_uncrossmatched_adult_male():
    res = BloodBankEngine.generate_emergency_uncrossmatched_release(patient_gender="male", patient_age=45)
    assert res["emergency_release"] is True
    assert res["recommended_blood_type"] == "O_POS"

def test_mtp_1_to_1_cooler_pack():
    res = BloodBankEngine.activate_massive_transfusion_cooler(mtp_round=1, fibrinogen_mg_dl=120.0)
    cooler = res["cooler_contents"]
    assert cooler["packed_red_blood_cells_units"] == 4
    assert cooler["fresh_frozen_plasma_units"] == 4
    assert cooler["platelets_apheresis_dose"] == 1
    assert cooler["cryoprecipitate_units"] == 10  # Low fibrinogen triggers cryo
    assert any("Tranexamic Acid" in h for h in res["adjunctive_hemostatics"])
