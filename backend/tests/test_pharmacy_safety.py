"""
Unit tests for Clinical Pharmacy Safety and Drug Interaction Engine.
"""

import pytest
from app.services.pharmacy_service import PharmacySafetyEngine, InteractionSeverity, PrescribeStatus

def test_safe_prescription():
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Atorvastatin",
        dosage="20mg PO QHS",
        active_medications=["Metformin", "Lisinopril"],
        patient_allergies=["Sulfa"],
        egfr=85.0
    )
    assert res["verdict"] == PrescribeStatus.APPROVED.value
    assert len(res["drug_interactions"]) == 0
    assert len(res["allergy_warnings"]) == 0
    assert res["renal_contraindication"] is None

def test_contraindicated_drug_drug_interaction():
    # Warfarin + Aspirin => severe bleeding risk
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Aspirin",
        dosage="325mg PO Daily",
        active_medications=["Warfarin"],
        patient_allergies=[],
        egfr=90.0
    )
    assert res["verdict"] == PrescribeStatus.BLOCKED.value
    assert len(res["drug_interactions"]) == 1
    assert res["drug_interactions"][0]["severity"] == InteractionSeverity.CONTRAINDICATED.value
    assert "hemorrhage" in res["drug_interactions"][0]["mechanism"]

def test_serotonin_syndrome_contraindication():
    # Fluoxetine + Selegiline
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Fluoxetine",
        dosage="20mg PO Daily",
        active_medications=["Selegiline"],
        patient_allergies=[]
    )
    assert res["verdict"] == PrescribeStatus.BLOCKED.value
    assert "Serotonin Syndrome" in res["drug_interactions"][0]["mechanism"]

def test_major_overridable_warning():
    # Lisinopril + Spironolactone => hyperkalemia
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Spironolactone",
        dosage="25mg PO Daily",
        active_medications=["Lisinopril"],
        patient_allergies=[],
        egfr=60.0
    )
    assert res["verdict"] == PrescribeStatus.WARNING_OVERRIDABLE.value
    assert len(res["drug_interactions"]) == 1
    assert res["drug_interactions"][0]["severity"] == InteractionSeverity.MAJOR.value

def test_direct_allergy_contraindication():
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Amoxicillin",
        dosage="500mg PO TID",
        active_medications=[],
        patient_allergies=["Amoxicillin"]
    )
    assert res["verdict"] == PrescribeStatus.BLOCKED.value
    assert len(res["allergy_warnings"]) == 1
    assert res["allergy_warnings"][0]["type"] == "DIRECT_ALLERGY"

def test_class_cross_reactivity_allergy():
    # Documented Penicillin allergy -> Blocks Ampicillin / Amoxicillin
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Ampicillin",
        dosage="500mg IV Q6H",
        active_medications=[],
        patient_allergies=["Penicillin"]
    )
    assert res["verdict"] == PrescribeStatus.BLOCKED.value
    assert len(res["allergy_warnings"]) == 1
    assert res["allergy_warnings"][0]["type"] == "CLASS_CROSS_REACTIVITY"

def test_renal_contraindication():
    # Metformin with eGFR < 30 contraindicated
    res = PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug="Metformin",
        dosage="1000mg PO BID",
        active_medications=[],
        patient_allergies=[],
        egfr=24.0
    )
    assert res["verdict"] == PrescribeStatus.BLOCKED.value
    assert res["renal_contraindication"] is not None
    assert res["renal_contraindication"]["severity"] == InteractionSeverity.CONTRAINDICATED.value
    assert "lactic acidosis" in res["renal_contraindication"]["message"]
