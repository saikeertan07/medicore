"""
Unit tests for ICU Telemetry and Predictive Bed Allocation Engine.
"""

import pytest
from app.services.bed_telemetry_service import (
    BedTelemetryEngine, WardCapacity, WardType
)

def test_hospital_census_and_icu_divert():
    wards = [
        WardCapacity(ward_type=WardType.ICU, total_beds=20, occupied_beds=19, isolation_beds=2),     # 95% -> critical divert
        WardCapacity(ward_type=WardType.EMERGENCY, total_beds=30, occupied_beds=20, isolation_beds=4),
        WardCapacity(ward_type=WardType.GENERAL, total_beds=100, occupied_beds=70, isolation_beds=10)
    ]
    census = BedTelemetryEngine.evaluate_hospital_census(wards)

    assert census["overall_total_beds"] == 150
    assert census["overall_occupied"] == 109
    assert census["overall_available"] == 41
    assert census["icu_divert_active"] is True
    assert census["emergency_status"] == "CRITICAL_DIVERT"
    assert census["wards"]["ICU"]["utilization_pct"] == 95.0

def test_step_down_readiness_stable_patient():
    # Stable patient with normalized NEWS2 and >24h ICU stay
    res = BedTelemetryEngine.evaluate_icu_discharge_readiness(
        patient_id=303,
        hours_in_icu=36,
        current_news2_score=1,
        is_hemodynamically_stable=True,
        on_vasopressors=False
    )
    assert res["ready_for_step_down"] is True
    assert res["target_ward"] == "GENERAL_STEP_DOWN"

def test_step_down_blocked_on_vasopressors():
    res = BedTelemetryEngine.evaluate_icu_discharge_readiness(
        patient_id=304,
        hours_in_icu=48,
        current_news2_score=2,
        is_hemodynamically_stable=True,
        on_vasopressors=True
    )
    assert res["ready_for_step_down"] is False
    assert "vasopressor" in res["reason"]

def test_ambulance_routing_divert_on_full_icu():
    wards = [
        WardCapacity(ward_type=WardType.ICU, total_beds=10, occupied_beds=10, isolation_beds=1),
        WardCapacity(ward_type=WardType.EMERGENCY, total_beds=20, occupied_beds=10, isolation_beds=2)
    ]
    census = BedTelemetryEngine.evaluate_hospital_census(wards)
    
    # Ambulance carrying critical ICU patient
    route = BedTelemetryEngine.route_incoming_ambulance(
        ambulance_id="MEDIC-44",
        triage_severity="CRITICAL",
        requires_icu=True,
        hospital_census=census
    )
    assert route["status"] == "DIVERT"
    assert "trauma center" in route["recommended_action"].lower()

def test_ambulance_routing_accepted():
    wards = [
        WardCapacity(ward_type=WardType.ICU, total_beds=20, occupied_beds=10, isolation_beds=1),
        WardCapacity(ward_type=WardType.EMERGENCY, total_beds=20, occupied_beds=5, isolation_beds=2)
    ]
    census = BedTelemetryEngine.evaluate_hospital_census(wards)

    route = BedTelemetryEngine.route_incoming_ambulance(
        ambulance_id="MEDIC-12",
        triage_severity="URGENT",
        requires_icu=False,
        hospital_census=census
    )
    assert route["status"] == "ACCEPT"
    assert "ED-RESUS-BAY" in route["assigned_bay"]
