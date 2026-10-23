"""
Unit tests for Ambient Clinical AI Scribe and SOAP generation.
"""

import pytest
from app.services.ambient_scribe_service import AmbientScribeEngine, ScribeNoteStatus

def test_icd10_keyword_extraction():
    transcript = "Patient has severe hypertension and was diagnosed with diabetes 5 years ago."
    matches = AmbientScribeEngine.match_icd10_codes(transcript)
    assert len(matches) >= 2
    codes = [m["code"] for m in matches]
    assert "I10" in codes
    assert "E11.9" in codes

def test_soap_note_generation():
    transcript = """
Doctor: What brings you in today?
Patient: I have had a severe headache and persistent fever for the past three days.
Doctor: Any chest pain or shortness of breath?
Patient: No, but the headache is throbbing.
Doctor: Let me check your lungs and heart. Lungs are clear, regular rate and rhythm.
Doctor: I am prescribing acetaminophen 500mg tablet BID and ordering blood tests.
"""
    note = AmbientScribeEngine.generate_soap_note(
        patient_id=101,
        encounter_id=505,
        raw_transcript=transcript,
        vitals_summary="BP 125/80, HR 82, Temp 38.4C"
    )

    assert note["patient_id"] == 101
    assert note["encounter_id"] == 505
    assert note["status"] == ScribeNoteStatus.DRAFT.value
    
    # Verify SOAP components exist
    soap = note["soap"]
    assert "headache" in soap["subjective"]["chief_complaint"].lower()
    assert "38.4C" in soap["objective"]["vital_signs"]
    assert len(soap["plan"]["pharmacotherapy"]) > 0

    # Verify ICD-10 suggestions
    icd = note["coding"]["suggested_icd10"]
    codes = [i["code"] for i in icd]
    assert "R51.9" in codes or "R50.9" in codes  # Headache or Fever
    assert note["compliance"]["requires_physician_attestation"] is True
