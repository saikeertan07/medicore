"""
Unit tests for Radiology DICOM AI Critical Finding Alerting.
"""

import pytest
from app.services.radiology_service import RadiologyAIEngine, CriticalFindingSeverity

def test_tension_pneumothorax_red_alert():
    report_text = """
EXAMINATION: Portable AP Chest Radiograph.
FINDINGS: Massive right-sided tension pneumothorax with complete collapse of the right lung,
shift of the mediastinum and trachea to the left, and flattening of the right hemidiaphragm.
IMPRESSION: Tension pneumothorax. Requires emergent decompression.
"""
    result = RadiologyAIEngine.inspect_radiology_report(
        study_id="STUDY-CXR-991",
        patient_id=404,
        modality="XRAY",
        body_part="CHEST",
        preliminary_radiologist_report=report_text
    )

    assert result["has_critical_findings"] is True
    assert result["requires_verbal_callback"] is True
    assert len(result["flagged_findings"]) == 1
    assert result["flagged_findings"][0]["severity"] == CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING.value
    assert result["flagged_findings"][0]["statutory_time_limit_mins"] == 15

def test_routine_imaging_no_critical_findings():
    report_text = """
EXAMINATION: CT Head without intravenous contrast.
FINDINGS: No acute intracranial hemorrhage, mass effect, or midline shift. Ventricles and sulci normal for age.
IMPRESSION: Normal non-contrast head CT.
"""
    result = RadiologyAIEngine.inspect_radiology_report(
        study_id="STUDY-CT-102",
        patient_id=405,
        modality="CT",
        body_part="BRAIN",
        preliminary_radiologist_report=report_text
    )

    assert result["has_critical_findings"] is False
    assert result["requires_verbal_callback"] is False
    assert len(result["flagged_findings"]) == 0
