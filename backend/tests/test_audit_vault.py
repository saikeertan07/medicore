"""
Unit tests for Cryptographic Tamper-Evident SHA-256 Audit Vault.
"""

import pytest
from app.services.audit_vault_service import AuditVault

def test_audit_vault_chaining():
    vault = AuditVault()
    e1 = vault.record_event(
        user_id=1,
        user_role="DOCTOR",
        action="VIEW_EHR",
        resource="Patient",
        resource_id="101"
    )
    e2 = vault.record_event(
        user_id=1,
        user_role="DOCTOR",
        action="UPDATE_PRESCRIPTION",
        resource="Prescription",
        resource_id="55",
        details={"med": "Lisinopril", "dose": "10mg"}
    )

    assert e1.entry_id == 1
    assert e2.entry_id == 2
    assert e2.previous_hash == e1.entry_hash
    assert len(e1.entry_hash) == 64
    assert len(e2.entry_hash) == 64

    # Verify integrity
    res = vault.verify_ledger_integrity()
    assert res["is_valid"] is True
    assert res["total_records"] == 2

def test_tamper_detection():
    vault = AuditVault()
    vault.record_event(1, "NURSE", "READ_VITALS", "Vitals", "99")
    vault.record_event(2, "ADMIN", "EXPORT_REPORT", "Report", "300")
    vault.record_event(3, "DOCTOR", "DISCHARGE_SUMMARY", "Discharge", "12")

    # Manually tamper with block 2 details
    vault.chain[1].details = {"illicit_alteration": "erased_audit"}

    res = vault.verify_ledger_integrity()
    assert res["is_valid"] is False
    assert res["tampered_entry_id"] == 2
    assert "tampering detected" in res["reason"]

def test_break_glass_logging():
    vault = AuditVault()
    bg = vault.record_break_glass_access(
        user_id=88,
        user_role="EMERGENCY_PHYSICIAN",
        patient_id=999,
        emergency_justification="Patient comatose in trauma bay after MVA. Immediate access to allergy history required."
    )

    assert bg.action == "EMERGENCY_BREAK_GLASS_ACCESS"
    assert bg.details["urgency"] == "LIFE_THREATENING_EMERGENCY"
    assert bg.details["compliance_alert_triggered"] is True
    
    # Verify ledger remains valid
    res = vault.verify_ledger_integrity()
    assert res["is_valid"] is True
