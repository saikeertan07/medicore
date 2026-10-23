"""
Unit tests for HL7 FHIR R4 Interoperability Engine.
"""

import pytest
from app.services.fhir_service import FHIRConverter, LOINC_CODES

def test_fhir_patient_resource():
    patient = FHIRConverter.to_fhir_patient(
        patient_id=402,
        mrn="MRN-884920",
        first_name="Eleanor",
        last_name="Vance",
        dob="1985-04-12",
        gender="female",
        phone="+1-555-0199",
        email="eleanor.vance@example.com"
    )

    assert patient["resourceType"] == "Patient"
    assert patient["id"] == "402"
    assert patient["active"] is True
    assert patient["name"][0]["family"] == "Vance"
    assert patient["name"][0]["given"] == ["Eleanor"]
    assert patient["gender"] == "female"
    assert patient["identifier"][0]["value"] == "MRN-884920"
    assert len(patient["telecom"]) == 2

def test_fhir_observation_loinc_coding():
    # Heart rate observation
    obs = FHIRConverter.to_fhir_observation(
        observation_id="OBS-HR-001",
        patient_id=402,
        vital_name="heart_rate",
        value=74.0
    )

    assert obs["resourceType"] == "Observation"
    assert obs["id"] == "OBS-HR-001"
    assert obs["status"] == "final"
    assert obs["code"]["coding"][0]["system"] == "http://loinc.org"
    assert obs["code"]["coding"][0]["code"] == "8867-4"
    assert obs["valueQuantity"]["value"] == 74.0
    assert obs["subject"]["reference"] == "Patient/402"

def test_fhir_bundle_assembly():
    patient = FHIRConverter.to_fhir_patient(
        patient_id=402,
        mrn="MRN-884920",
        first_name="Eleanor",
        last_name="Vance",
        dob="1985-04-12",
        gender="female"
    )
    obs1 = FHIRConverter.to_fhir_observation("OBS-1", 402, "systolic_bp", 124.0)
    obs2 = FHIRConverter.to_fhir_observation("OBS-2", 402, "spo2", 99.0)

    bundle = FHIRConverter.create_fhir_patient_bundle(patient, [obs1, obs2])
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 3
    assert len(bundle["entry"]) == 3
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][1]["resource"]["resourceType"] == "Observation"
