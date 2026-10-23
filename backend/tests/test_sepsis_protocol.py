"""
Unit tests for Sepsis 3.0 & Surviving Sepsis Campaign Protocol.
"""

import pytest
from app.services.sepsis_engine import SepsisProtocolEngine, SepsisRiskLevel

def test_qsofa_positive_score():
    # SBP 95 (<=100: +1), RR 24 (>=22: +1), GCS altered (+1) => score 3
    qsofa = SepsisProtocolEngine.calculate_qsofa(
        systolic_bp=95,
        respiration_rate=24,
        altered_mentation=True
    )
    assert qsofa["qsofa_score"] == 3
    assert qsofa["is_positive"] is True

def test_code_sepsis_activation_and_bundle():
    res = SepsisProtocolEngine.evaluate_sepsis_protocol(
        patient_id=701,
        systolic_bp=92,
        heart_rate=115,
        respiration_rate=26,
        temperature=39.2,
        altered_mentation=True,
        suspected_infection_source="Urinary Tract (Pyelonephritis)",
        serum_lactate=3.2
    )

    assert res["requires_emergency_code_sepsis"] is True
    assert res["risk_level"] == SepsisRiskLevel.CRITICAL_SEPSIS_ALERT.value
    assert len(res["one_hour_sepsis_bundle"]) == 5
    assert "CODE SEPSIS ACTIVATED" in res["clinical_escalation_protocol"]

def test_septic_shock_trigger():
    # Hypotension + Lactate >= 4.0 => Septic Shock
    res = SepsisProtocolEngine.evaluate_sepsis_protocol(
        patient_id=702,
        systolic_bp=82,
        heart_rate=130,
        respiration_rate=28,
        temperature=39.5,
        altered_mentation=True,
        suspected_infection_source="Pneumonia",
        serum_lactate=4.8
    )
    assert res["risk_level"] == SepsisRiskLevel.SEPTIC_SHOCK.value
    assert res["requires_emergency_code_sepsis"] is True
