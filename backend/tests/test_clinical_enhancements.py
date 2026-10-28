import pytest
from fastapi import HTTPException
from app.schemas.schemas import VitalsCreate
from app.services.clinical_service import validate_vitals_values
from app.services.triage_ai_service import triage_ai_service
from app.services.lab_service import detect_critical_panic_flag, AbnormalFlag


def test_vitals_pulse_pressure_and_oxygen_validation():
    """
    Validates that vitals physiological boundary rules catch invalid pulse pressure
    and extreme oxygen saturation entries.
    """
    # Valid vitals pass without exception
    valid_vitals = VitalsCreate(
        systolic_bp=120,
        diastolic_bp=80,
        heart_rate=72,
        respiratory_rate=16,
        oxygen_saturation=98.0
    )
    validate_vitals_values(valid_vitals)

    # Inverted BP: systolic <= diastolic raises 422
    inverted_bp = VitalsCreate(systolic_bp=80, diastolic_bp=120)
    with pytest.raises(HTTPException) as exc_info:
        validate_vitals_values(inverted_bp)
    assert exc_info.value.status_code == 422
    assert "greater than diastolic" in exc_info.value.detail

    # Critically narrow pulse pressure (< 10 mmHg) raises 422
    narrow_pp = VitalsCreate(systolic_bp=95, diastolic_bp=90)
    with pytest.raises(HTTPException) as exc_info:
        validate_vitals_values(narrow_pp)
    assert exc_info.value.status_code == 422
    assert "pulse pressure" in exc_info.value.detail.lower()

    # Extreme invalid SpO2 bypassing pydantic schema triggers service check
    high_spo2 = VitalsCreate.model_construct(systolic_bp=120, diastolic_bp=80, oxygen_saturation=105.0)
    with pytest.raises(HTTPException) as exc_info:
        validate_vitals_values(high_spo2)
    assert exc_info.value.status_code == 422
    assert "Oxygen saturation" in exc_info.value.detail


def test_news2_supplemental_oxygen_scoring():
    """
    Validates RCP NEWS2 guidelines where supplemental oxygen adds +2 points.
    """
    baseline_vitals = {
        "respiratory_rate": 16,
        "oxygen_saturation": 98,
        "blood_pressure_systolic": 120,
        "heart_rate": 72,
        "temperature_celsius": 37.0,
        "consciousness": "ALERT"
    }

    # Room air baseline: score 0
    score_room_air = triage_ai_service.calculate_news2(baseline_vitals)
    assert score_room_air == 0

    # Supplemental O2 added: score becomes 2
    vitals_on_o2 = dict(baseline_vitals)
    vitals_on_o2["supplemental_oxygen"] = True
    score_on_o2 = triage_ai_service.calculate_news2(vitals_on_o2)
    assert score_on_o2 == 2


def test_news2_hypercapnic_copd_scale_2_scoring():
    """
    Validates NEWS2 Scale 2 for hypercapnic respiratory failure (target SpO2 88-92%).
    """
    # SpO2 90% in standard scale 1 = 3 points (severe hypoxemia)
    vitals_hypox = {
        "respiratory_rate": 16,
        "oxygen_saturation": 90,
        "blood_pressure_systolic": 120,
        "heart_rate": 72,
        "temperature_celsius": 37.0,
        "consciousness": "ALERT",
        "copd_scale_2": False
    }
    assert triage_ai_service.calculate_news2(vitals_hypox) == 3

    # SpO2 90% in COPD Scale 2 = 0 points (within therapeutic target 88-92%)
    vitals_copd_target = dict(vitals_hypox)
    vitals_copd_target["copd_scale_2"] = True
    assert triage_ai_service.calculate_news2(vitals_copd_target) == 0

    # SpO2 82% in COPD Scale 2 = 3 points (critically low even for hypercapnia)
    vitals_copd_critical = dict(vitals_hypox)
    vitals_copd_critical["copd_scale_2"] = True
    vitals_copd_critical["oxygen_saturation"] = 82
    assert triage_ai_service.calculate_news2(vitals_copd_critical) == 3


def test_lab_critical_panic_value_auto_detection():
    """
    Verifies that critical panic laboratory thresholds are flagged as CRITICAL.
    """
    # Severe Hypokalemia (K+ < 2.8 mmol/L)
    assert detect_critical_panic_flag("Serum Potassium", 2.4, AbnormalFlag.NORMAL) == AbnormalFlag.CRITICAL

    # Severe Hyperkalemia (K+ > 6.2 mmol/L)
    assert detect_critical_panic_flag("Potassium, Serum", 6.9, AbnormalFlag.NORMAL) == AbnormalFlag.CRITICAL

    # Normal Potassium (4.0 mmol/L) preserves original flag
    assert detect_critical_panic_flag("Serum Potassium", 4.0, AbnormalFlag.NORMAL) == AbnormalFlag.NORMAL

    # Severe Hypoglycemia (Glucose < 45 mg/dL)
    assert detect_critical_panic_flag("Blood Glucose", 38.0, AbnormalFlag.LOW) == AbnormalFlag.CRITICAL

    # Hyperglycemic crisis (Glucose > 450 mg/dL)
    assert detect_critical_panic_flag("Fasting Blood Glucose", 495.0, AbnormalFlag.HIGH) == AbnormalFlag.CRITICAL

    # Severe Thrombocytopenia (Platelets < 20k)
    assert detect_critical_panic_flag("Platelet Count", 14.0, AbnormalFlag.LOW) == AbnormalFlag.CRITICAL

    # Critical Anemia (Hemoglobin < 6.0 g/dL)
    assert detect_critical_panic_flag("Hemoglobin (Hgb)", 5.1, AbnormalFlag.NORMAL) == AbnormalFlag.CRITICAL
