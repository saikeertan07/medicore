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

def test_airway_npo_fasting_compliance():
    # 8 hours fasting after light meal -> compliant
    req_compliant = AirwayEvaluationRequest(
        patient_id="anes-003",
        mallampati_class=1,
        fasting_hours=8.0,
        last_intake_type="light_meal"
    )
    res_compliant = AnesthesiaAirwayService.evaluate_airway(req_compliant)
    npo = res_compliant["npo_fasting_assessment"]
    assert npo is not None
    assert npo["npo_guidelines_met"] is True
    assert npo["aspiration_risk"] is False

    # 3 hours fasting after heavy meal -> non-compliant (requires 8h)
    req_non_compliant = AirwayEvaluationRequest(
        patient_id="anes-004",
        mallampati_class=2,
        fasting_hours=3.0,
        last_intake_type="heavy_meal"
    )
    res_non_compliant = AnesthesiaAirwayService.evaluate_airway(req_non_compliant)
    npo_fail = res_non_compliant["npo_fasting_assessment"]
    assert npo_fail is not None
    assert npo_fail["npo_guidelines_met"] is False
    assert npo_fail["aspiration_risk"] is True
    assert "Rapid Sequence Induction" in npo_fail["aspiration_mitigation"]

