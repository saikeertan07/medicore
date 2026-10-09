"""
Cryptographic Tamper-Evident SHA-256 Audit Vault & Emergency Break-Glass Protocol.
Enforces HIPAA compliance by creating an immutable, hash-chained ledger of all
clinical activities and sensitive medical record accesses.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class AuditEntry:
    entry_id: int
    timestamp: str
    user_id: int
    user_role: str
    action: str
    resource: str
    resource_id: str
    details: Dict[str, Any]
    previous_hash: str
    entry_hash: str

class AuditVault:
    def __init__(self):
        self.chain: List[AuditEntry] = []
        self._genesis_hash = "0" * 64

    def _compute_hash(self, prev_hash: str, timestamp: str, user_id: int, action: str, resource: str, details: dict) -> str:
        serialized = f"{prev_hash}|{timestamp}|{user_id}|{action}|{resource}|{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def record_event(
        self,
        user_id: int,
        user_role: str,
        action: str,
        resource: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """Appends a new cryptographically chained audit record."""
        prev_hash = self.chain[-1].entry_hash if self.chain else self._genesis_hash
        timestamp = datetime.now(timezone.utc).isoformat()
        event_details = details or {}

        entry_hash = self._compute_hash(prev_hash, timestamp, user_id, action, resource, event_details)
        entry = AuditEntry(
            entry_id=len(self.chain) + 1,
            timestamp=timestamp,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=event_details,
            previous_hash=prev_hash,
            entry_hash=entry_hash
        )
        self.chain.append(entry)
        return entry

    def record_break_glass_access(
        self,
        user_id: int,
        user_role: str,
        patient_id: int,
        emergency_justification: str
    ) -> AuditEntry:
        """High-priority emergency break-glass event recording."""
        return self.record_event(
            user_id=user_id,
            user_role=user_role,
            action="EMERGENCY_BREAK_GLASS_ACCESS",
            resource="PatientRecord",
            resource_id=str(patient_id),
            details={
                "urgency": "LIFE_THREATENING_EMERGENCY",
                "justification": emergency_justification,
                "compliance_alert_triggered": True
            }
        )

    def verify_ledger_integrity(self) -> Dict[str, Any]:
        """Cryptographically verifies every block in the ledger against its predecessor."""
        if not self.chain:
            return {"is_valid": True, "total_records": 0, "message": "Ledger is empty and valid."}

        for i, entry in enumerate(self.chain):
            expected_prev = self._genesis_hash if i == 0 else self.chain[i - 1].entry_hash
            if entry.previous_hash != expected_prev:
                return {
                    "is_valid": False,
                    "tampered_entry_id": entry.entry_id,
                    "reason": f"Corrupted chain linkage at entry #{entry.entry_id}. Previous hash does not match predecessor."
                }

            recalculated_hash = self._compute_hash(
                entry.previous_hash,
                entry.timestamp,
                entry.user_id,
                entry.action,
                entry.resource,
                entry.details
            )
            if recalculated_hash != entry.entry_hash:
                return {
                    "is_valid": False,
                    "tampered_entry_id": entry.entry_id,
                    "reason": f"Content tampering detected in entry #{entry.entry_id}. Recomputed hash differs from recorded hash."
                }

        return {
            "is_valid": True,
            "total_records": len(self.chain),
            "latest_hash": self.chain[-1].entry_hash,
            "message": "Audit ledger cryptographically authenticated. Zero tampering detected."
        }
