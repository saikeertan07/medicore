"""
Comprehensive unit tests for NEWS2 and ESI Emergency Triage Engine.
"""

import pytest
from app.services.triage_service import TriageEngine, VitalSigns, NEWS2RiskLevel, ESILevel

def test_normal_patient_news2():
    # Healthy adult vitals
    vitals = VitalSigns(
        respiration_rate=16,
        spo2=98,
        on_oxygen=False,
        systolic_bp=120,
        heart_rate=72,
        consciousness="ALERT",
        temperature=37.0
    )
    result = TriageEngine.evaluate_news2(vitals)
    assert result["total_score"] == 0
    assert result["risk_level"] == NEWS2RiskLevel.LOW.value
    assert result["has_extreme_single_trigger"] is False
    assert "STABLE" in result["clinical_escalation_protocol"]

def test_deteriorating_patient_high_news2():
    # Severe septic / respiratory deterioration
    vitals = VitalSigns(
        respiration_rate=28,       # 3 points
        spo2=90,                   # 3 points
        on_oxygen=True,            # 2 points
        systolic_bp=88,            # 3 points
        heart_rate=135,            # 3 points
        consciousness="VOICE",     # 3 points
        temperature=39.5           # 2 points
    )
    result = TriageEngine.evaluate_news2(vitals)
    assert result["total_score"] == 19
    assert result["risk_level"] == NEWS2RiskLevel.HIGH.value
    assert result["has_extreme_single_trigger"] is True
    assert "EMERGENCY" in result["clinical_escalation_protocol"]
    assert "Critical Care" in result["clinical_escalation_protocol"]

def test_extreme_single_trigger_medium_risk():
    # Normal vitals except extreme bradycardia (HR <= 40 => 3 pts)
    vitals = VitalSigns(
        respiration_rate=14,       # 0
        spo2=98,                   # 0
        on_oxygen=False,           # 0
        systolic_bp=125,           # 0
        heart_rate=38,             # 3
        consciousness="ALERT",     # 0
        temperature=36.8           # 0
    )
    result = TriageEngine.evaluate_news2(vitals)
    assert result["total_score"] == 3
    assert result["has_extreme_single_trigger"] is True
    assert result["risk_level"] == NEWS2RiskLevel.MEDIUM.value

def test_esi_level_1_resuscitation():
    vitals = VitalSigns(
        respiration_rate=4,
        spo2=75,
        on_oxygen=True,
        systolic_bp=60,
        heart_rate=25,
        consciousness="UNRESPONSIVE",
        temperature=34.5
    )
    esi = TriageEngine.evaluate_esi(vitals, chief_complaint="Cardiac arrest", resources_needed=3)
    assert esi["esi_level"] == ESILevel.RESUSCITATION.value
    assert "Resuscitation" in esi["category"]

def test_esi_level_2_emergent():
    vitals = VitalSigns(
        respiration_rate=18,
        spo2=96,
        on_oxygen=False,
        systolic_bp=130,
        heart_rate=80,
        consciousness="ALERT",
        temperature=37.1
    )
    esi = TriageEngine.evaluate_esi(vitals, chief_complaint="Severe chest pain radiating to jaw", resources_needed=3)
    assert esi["esi_level"] == ESILevel.EMERGENT.value
    assert "Emergent" in esi["category"]

def test_esi_level_3_urgent():
    vitals = VitalSigns(
        respiration_rate=16,
        spo2=98,
        on_oxygen=False,
        systolic_bp=120,
        heart_rate=75,
        consciousness="ALERT",
        temperature=37.0
    )
    esi = TriageEngine.evaluate_esi(vitals, chief_complaint="Abdominal pain for 2 days", resources_needed=2)
    assert esi["esi_level"] == ESILevel.URGENT.value

def test_esi_level_5_non_urgent():
    vitals = VitalSigns(
        respiration_rate=16,
        spo2=98,
        on_oxygen=False,
        systolic_bp=120,
        heart_rate=72,
        consciousness="ALERT",
        temperature=36.9
    )
    esi = TriageEngine.evaluate_esi(vitals, chief_complaint="Prescription refill", resources_needed=0)
    assert esi["esi_level"] == ESILevel.NON_URGENT.value
