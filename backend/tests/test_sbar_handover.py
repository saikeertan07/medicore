"""
Unit tests for SBAR Shift Handover Engine.
"""

import pytest
from app.services.sbar_handover_service import SBARHandoverEngine

def test_sbar_handover_generation():
    vitals = {
        "heart_rate": 88,
        "systolic_bp": 118,
        "spo2": 97,
        "temperature": 37.1,
        "news2_score": 1
    }
    report = SBARHandoverEngine.generate_sbar_handover(
        patient_id=202,
        patient_name="Arthur Pendelton",
        room_number="ICU-Bed-04",
        attending_doctor="Dr. Chen",
        primary_diagnosis="Post-operative coronary artery bypass graft (CABG)",
        admission_date="2026-10-15",
        allergies=["Penicillin"],
        vitals=vitals,
        active_medications=["Aspirin 81mg", "Atorvastatin 40mg", "Metoprolol 25mg"],
        abnormal_labs=["Mild hypokalemia K+ 3.4 mmol/L"],
        pending_orders=["Morning electrolyte panel", "Chest X-ray portable"]
    )

    sbar = report["sbar"]
    assert "Arthur Pendelton" in sbar["situation"]["patient_identification"]
    assert "ICU-Bed-04" in sbar["situation"]["room_location"]
    assert "Penicillin" in sbar["background"]["documented_allergies"]
    assert sbar["assessment"]["news2_deterioration_score"] == 1
    assert sbar["assessment"]["clinical_stability_risk"] == "STABLE"
    assert len(sbar["recommendation"]["action_items_for_incoming_shift"]) >= 2
