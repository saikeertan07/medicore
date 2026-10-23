import pytest
from app.services.anesthesia_airway_service import (
    AnesthesiaAirwayService,
    AirwayEvaluationRequest
)

def test_airway_routine():
    # Class I, 3-3-2 met, no obstacles -> LEMON 0
    req = AirwayEvaluationRequest(
        patient_id="anes-001",
        mallampati_class=1,
        look_abnormal_external=False,
        rule_3_3_2_met=True,
        has_airway_obstruction=False,
        limited_neck_mobility=False
    )
    result = AnesthesiaAirwayService.evaluate_airway(req)
    assert result["lemon_score"] == 0
    assert result["airway_risk_classification"] == "ROUTINE_PREDICTED_NORMAL_AIRWAY"
    assert "Class I: Soft palate" in result["mallampati_description"]

def test_airway_critical_difficult():
    # Class IV, failed 3-3-2, c-spine collar -> LEMON = 3 -> CRITICAL
    req = AirwayEvaluationRequest(
        patient_id="anes-002",
        mallampati_class=4,
        look_abnormal_external=False,
        rule_3_3_2_met=False,
        has_airway_obstruction=False,
        limited_neck_mobility=True,
        prior_difficult_intubation_history=True
    )
    result = AnesthesiaAirwayService.evaluate_airway(req)
    assert result["lemon_score"] == 3
    assert result["airway_risk_classification"] == "CRITICAL_DIFFICULT_AIRWAY"
    # Verify rescue equipment includes Video Laryngoscope, Bougie, and cricothyrotomy kit
    plan_text = " ".join(result["asa_airway_equipment_readiness"])
    assert "video laryngoscope" in plan_text.lower()
    assert "bougie" in plan_text.lower()
    assert "cricothyrotomy" in plan_text.lower()
