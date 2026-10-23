"""
Unit tests for Code Blue & AHA ACLS Resuscitation Engine.
"""

import pytest
from app.services.acls_resuscitation_service import (
    ACLSResuscitationEngine, CardiacRhythm, RhythmCategory
)

def test_shockable_rhythm_vf():
    res = ACLSResuscitationEngine.evaluate_resuscitation_step(
        current_rhythm="VENTRICULAR_FIBRILLATION",
        cpr_cycle_number=1,
        total_shocks_delivered=0,
        epinephrine_doses_given=0,
        amiodarone_doses_given=0
    )
    assert res["is_shockable"] is True
    assert res["category"] == RhythmCategory.SHOCKABLE.value
    assert "SHOCK RECOMMENDED" in res["immediate_actions"][0]
    assert "defibrillation shock #1" in res["immediate_actions"][0]

def test_shock_refractory_vf_amiodarone_trigger():
    # After 2 shocks delivered, amiodarone dose 1 is due
    res = ACLSResuscitationEngine.evaluate_resuscitation_step(
        current_rhythm="VF",
        cpr_cycle_number=3,
        total_shocks_delivered=2,
        epinephrine_doses_given=1,
        amiodarone_doses_given=0
    )
    assert res["is_shockable"] is True
    med_names = [m["drug"] for m in res["medications_due"]]
    assert any("Amiodarone (First Dose)" in m for m in med_names)

def test_non_shockable_asystole():
    res = ACLSResuscitationEngine.evaluate_resuscitation_step(
        current_rhythm="ASYSTOLE",
        cpr_cycle_number=1,
        total_shocks_delivered=0,
        epinephrine_doses_given=0,
        amiodarone_doses_given=0
    )
    assert res["is_shockable"] is False
    assert "NO SHOCK" in res["immediate_actions"][0]
    assert any("Epinephrine" in m["drug"] for m in res["medications_due"])
    assert "STAT" in res["medications_due"][0]["dose"]
