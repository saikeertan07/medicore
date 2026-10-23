import sys
import os
import requests
import psycopg2
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000/api/v1"
DB_URL = "postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db"

print("=" * 75)
print("MEDICORE AI — STEP 4 COMPLETE AUTHORITATIVE LABORATORY WORKFLOW VERIFICATION")
print("=" * 75)

def login(email, password):
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise Exception(f"Login failed for {email}: {res.status_code} - {res.text}")
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. System Health Check
print("\n[CHECK 1] System & PostgreSQL Engine Health")
res = requests.get(f"{BASE_URL}/health")
assert res.status_code == 200, f"Health check failed: {res.text}"
health = res.json()
assert health["database"] == "healthy"
assert health["database_engine"] == "postgresql"
print(f"  PASS: Backend reports healthy PostgreSQL engine ({health['environment']})")

# 2. Lab Catalog Verification
print("\n[CHECK 2] Standard Laboratory Test Catalog (10 Standard Tests)")
admin_headers = login("admin@medicore.ai", "Admin@123")
res = requests.get(f"{BASE_URL}/lab/tests", headers=admin_headers)
assert res.status_code == 200, f"Catalog fetch failed: {res.text}"
catalog = res.json()
assert len(catalog) >= 10, f"Expected at least 10 lab tests, found {len(catalog)}"
codes = [t["code"] for t in catalog]
for expected_code in ["CBC", "HGB", "WBC", "PLT", "GLU", "CREAT", "ALT", "AST", "LIPID", "TSH"]:
    assert expected_code in codes, f"Expected lab test {expected_code} missing from catalog"
print(f"  PASS: Retrieved {len(catalog)} active catalog tests with standard reference ranges and units.")

# 3. Create Patient & Encounter for Doctor 1 (Dr. Marcus Chen, Cardiology)
print("\n[CHECK 3] Create Patient and Clinical Encounter")
doc1_headers = login("doctor.chen@medicore.ai", "Doctor@123")
doc2_headers = login("doctor.martinez@medicore.ai", "Doctor@123")  # Same department (Cardiology)
rec_headers = login("receptionist@medicore.ai", "Reception@123")
nurse_headers = login("nurse.sarah@medicore.ai", "Nurse@123")

ts = int(datetime.utcnow().timestamp())
pat_email = f"lab_pat_{ts}@example.com"
pat_pass = "PatientPass123!"
reg_payload = {
    "full_name": f"Lab Patient {ts}",
    "email": pat_email,
    "password": pat_pass,
    "phone": f"+1555{ts % 1000000:06d}"
}
res = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
assert res.status_code in [200, 201], f"Patient registration failed: {res.text}"
pat_data = res.json()
pat_id = pat_data["patient_id"]
pat_headers = {"Authorization": f"Bearer {pat_data['access_token']}"}
print(f"  PASS: Registered Patient #{pat_id} ({pat_email}) with portal access")

# Doctor 1 is Dr. Marcus Chen (id=1, attending)
res = requests.post(f"{BASE_URL}/encounters", json={
    "patient_id": pat_id,
    "attending_doctor_id": 1,
    "department_id": 1,
    "encounter_type": "OUTPATIENT"
}, headers=doc1_headers)
assert res.status_code == 201, f"Encounter creation failed: {res.text}"
enc = res.json()
enc_id = enc["id"]
print(f"  PASS: Created Clinical Encounter #{enc_id} ({enc['encounter_number']}) with Attending Doctor #1")

# 4. Same-Department Doctor Object-Level Authorization Check
print("\n[CHECK 4] Same-Department Doctor Object-Level Authorization Check")
cbc_def = next(t for t in catalog if t["code"] == "CBC")
glu_def = next(t for t in catalog if t["code"] == "GLU")
tsh_def = next(t for t in catalog if t["code"] == "TSH")

# Dr. Martinez (Doctor 2, same department Cardiology) attempts to place order on Dr. Chen's encounter -> 403
res = requests.post(f"{BASE_URL}/lab/orders", json={
    "patient_id": pat_id,
    "encounter_id": enc_id,
    "priority": "STAT",
    "clinical_indication": "Unauthorized order attempt by Dr. Martinez",
    "items": [{"test_id": cbc_def["id"]}]
}, headers=doc2_headers)
assert res.status_code == 403, f"Expected 403 for same-dept doctor order on Dr. Chen's encounter, got {res.status_code}"
print("  PASS: Dr. Martinez (same department Cardiology) blocked from ordering on Dr. Chen's encounter (403).")

# 5. Attending Doctor Orders Laboratory Tests (Happy Path)
print("\n[CHECK 5] Attending Doctor Places Laboratory Order")
order_payload = {
    "patient_id": pat_id,
    "encounter_id": enc_id,
    "priority": "STAT",
    "clinical_indication": "Evaluation of acute syncope, fatigue, and suspected anemia",
    "notes": "Urgent stat processing requested",
    "items": [
        {"test_id": cbc_def["id"], "notes": "Fasting blood draw"},
        {"test_id": glu_def["id"], "notes": "Fingerstick or plasma"},
        {"test_id": tsh_def["id"], "notes": "Serum tube for rejection test"}
    ]
}

# Negative test: Receptionist cannot place orders (403)
res = requests.post(f"{BASE_URL}/lab/orders", json=order_payload, headers=rec_headers)
assert res.status_code == 403
print("  PASS: Receptionist cannot place laboratory orders (403 Forbidden).")

# Dr. Chen places order
res = requests.post(f"{BASE_URL}/lab/orders", json=order_payload, headers=doc1_headers)
assert res.status_code == 201, f"Doctor lab order placement failed: {res.text}"
lab_order = res.json()
order_id = lab_order["id"]
assert lab_order["order_number"].startswith("LAB-")
assert lab_order["status"] == "ORDERED"
assert len(lab_order["items"]) == 3
cbc_item = next(i for i in lab_order["items"] if i["test_id"] == cbc_def["id"])
glu_item = next(i for i in lab_order["items"] if i["test_id"] == glu_def["id"])
tsh_item = next(i for i in lab_order["items"] if i["test_id"] == tsh_def["id"])
print(f"  PASS: Doctor placed Order #{order_id} ({lab_order['order_number']}) with 3 items [LAB_ORDER_CREATED]")

# 6. Order Cancellation Flow (Audit Event: LAB_ORDER_CANCELLED)
print("\n[CHECK 6] Doctor Order Cancellation Flow (LAB_ORDER_CANCELLED)")
res_cancel_order = requests.post(f"{BASE_URL}/lab/orders", json={
    "patient_id": pat_id,
    "encounter_id": enc_id,
    "priority": "ROUTINE",
    "clinical_indication": "Order created to verify cancellation",
    "items": [{"test_id": cbc_def["id"]}]
}, headers=doc1_headers)
assert res_cancel_order.status_code == 201
cancel_order_id = res_cancel_order.json()["id"]

# Same-department Doctor 2 attempts to cancel Doctor 1's order -> 403
res = requests.post(
    f"{BASE_URL}/lab/orders/{cancel_order_id}/cancel",
    json={"reason": "Unauthorized cancellation attempt"},
    headers=doc2_headers
)
assert res.status_code == 403
print("  PASS: Same-department doctor blocked from cancelling Doctor 1's order (403 Forbidden).")

# Doctor 1 cancels own order
res = requests.post(
    f"{BASE_URL}/lab/orders/{cancel_order_id}/cancel",
    json={"reason": "Duplicate diagnostic request cancelled by attending physician"},
    headers=doc1_headers
)
assert res.status_code == 200
assert res.json()["status"] == "CANCELLED"
print(f"  PASS: Doctor successfully cancelled Order #{cancel_order_id} [LAB_ORDER_CANCELLED]")

# 7. Staff Qualification Boundary Check
print("\n[CHECK 7] Staff Qualification Boundary Verification")
# Receptionist attempts to collect sample -> 403
res = requests.post(
    f"{BASE_URL}/lab/orders/{order_id}/samples",
    json={"specimen_type": "Venous Whole Blood", "item_ids": [cbc_item["id"]]},
    headers=rec_headers
)
assert res.status_code == 403, f"Expected 403 for unqualified staff sample collection, got {res.status_code}"
print("  PASS: Unqualified staff blocked from collecting laboratory samples (403 Forbidden).")

# 8. Specimen Collection (Audit Event: LAB_SAMPLE_COLLECTED)
print("\n[CHECK 8] Phlebotomy Specimen Collection (LAB_SAMPLE_COLLECTED)")
# Sample 1: Venous Whole Blood for CBC and GLU (Valid specimen)
collect_payload = {
    "specimen_type": "Venous Whole Blood",
    "item_ids": [cbc_item["id"], glu_item["id"]]
}
res = requests.post(f"{BASE_URL}/lab/orders/{order_id}/samples", json=collect_payload, headers=nurse_headers)
assert res.status_code == 201
sample1 = res.json()
sample1_id = sample1["id"]
assert sample1["accession_number"].startswith("ACC-")
assert sample1["status"] == "COLLECTED"

# Sample 2: Serum for TSH (Will be rejected for QC)
res2 = requests.post(
    f"{BASE_URL}/lab/orders/{order_id}/samples",
    json={"specimen_type": "Serum", "item_ids": [tsh_item["id"]]},
    headers=nurse_headers
)
assert res2.status_code == 201
sample2 = res2.json()
sample2_id = sample2["id"]
print(f"  PASS: Collected Specimen #{sample1_id} ({sample1['accession_number']}) and #{sample2_id} [LAB_SAMPLE_COLLECTED]")

# 9. Specimen Rejection Flow (Audit Event: LAB_SAMPLE_REJECTED)
print("\n[CHECK 9] Central Laboratory Specimen Rejection Flow (LAB_SAMPLE_REJECTED)")
res = requests.post(
    f"{BASE_URL}/lab/samples/{sample2_id}/reject",
    json={"rejection_reason": "Gross hemolysis detected; tube unsuitable for immunoassay analysis"},
    headers=nurse_headers
)
assert res.status_code == 200
rejected_sample = res.json()
assert rejected_sample["status"] == "REJECTED"
assert "hemolysis" in rejected_sample["rejection_reason"]
print(f"  PASS: Specimen #{sample2_id} rejected with recorded clinical rationale [LAB_SAMPLE_REJECTED]")

# 10. Central Laboratory Reception & Processing Started (LAB_SAMPLE_RECEIVED & LAB_PROCESSING_STARTED)
print("\n[CHECK 10] Central Laboratory Accessioning Intake & Processing Started")
res = requests.post(
    f"{BASE_URL}/lab/samples/{sample1_id}/receive",
    json={"notes": "Specimen received intact, no hemolysis"},
    headers=nurse_headers
)
assert res.status_code == 200
recv_sample = res.json()
assert recv_sample["status"] == "RECEIVED"
print(f"  PASS: Specimen #{sample1_id} received into laboratory analyzer queue [LAB_SAMPLE_RECEIVED & LAB_PROCESSING_STARTED]")

# 11. Diagnostic Result Entry (Audit Event: LAB_RESULT_ENTERED)
print("\n[CHECK 11] Diagnostic Analyzer Result Entry (LAB_RESULT_ENTERED)")
# Unqualified receptionist attempts result entry -> 403
res = requests.post(
    f"{BASE_URL}/lab/order-items/{cbc_item['id']}/results",
    json={"value": "6.9", "numeric_value": 6.9, "abnormal_flag": "CRITICAL"},
    headers=rec_headers
)
assert res.status_code == 403
print("  PASS: Unqualified staff blocked from entering diagnostic results (403 Forbidden).")

# Qualified nurse enters critical low hemoglobin result
res1_payload = {
    "value": "6.9",
    "numeric_value": 6.9,
    "unit": "g/dL",
    "reference_range": "12.0 - 17.5 g/dL",
    "abnormal_flag": "CRITICAL",
    "comments": "Critical microcytic anemia observed. Verified on automated analyzer."
}
res = requests.post(f"{BASE_URL}/lab/order-items/{cbc_item['id']}/results", json=res1_payload, headers=nurse_headers)
assert res.status_code == 201
result1 = res.json()
result1_id = result1["id"]
assert result1["status"] == "ENTERED"
assert result1["abnormal_flag"] == "CRITICAL"
print(f"  PASS: Result #{result1_id} entered: {result1['value']} {result1['unit']} (CRITICAL) [LAB_RESULT_ENTERED]")

# 12. Patient Confidentiality Shield Verification
print("\n[CHECK 12] Patient Confidentiality Shield (Unverified Results)")
res = requests.get(f"{BASE_URL}/lab/patients/{pat_id}/results", headers=pat_headers)
assert res.status_code == 200
pat_view = res.json()
unverified_matches = [r for r in pat_view if r["id"] == result1_id]
assert len(unverified_matches) == 0, "SECURITY VIOLATION: Patient viewed unverified draft result!"
print("  PASS: Draft (ENTERED) results are completely shielded from patients.")

# 13. Physician Result Verification (Audit Events: LAB_RESULT_VERIFIED & LAB_RESULT_FINALIZED)
print("\n[CHECK 13] Physician Result Verification & Finalization")
# Doctor 2 (same department, but not attending/ordering) attempts to verify -> 403
res = requests.post(
    f"{BASE_URL}/lab/results/{result1_id}/verify",
    json={"comments": "Unauthorized verification by Dr. Martinez"},
    headers=doc2_headers
)
assert res.status_code == 403, f"Expected 403 for same-dept doctor verification, got {res.status_code}"
print("  PASS: Dr. Martinez (same department) blocked from verifying Doctor Chen's result (403 Forbidden).")

# Attending Doctor 1 verifies and finalizes
res = requests.post(
    f"{BASE_URL}/lab/results/{result1_id}/verify",
    json={"comments": "Attending physician reviewed critical low hemoglobin. Transfusion protocol evaluated."},
    headers=doc1_headers
)
assert res.status_code == 200
verified_res = res.json()
assert verified_res["status"] == "FINAL"
assert verified_res["verified_at"] is not None
print(f"  PASS: Result #{result1_id} verified and finalized by Dr. Marcus Chen [LAB_RESULT_VERIFIED & LAB_RESULT_FINALIZED]")

# Concurrency collision / idempotency: re-verify must return 409
re_res = requests.post(f"{BASE_URL}/lab/results/{result1_id}/verify", json={}, headers=doc1_headers)
assert re_res.status_code == 409
print("  PASS: Re-verification rejected with HTTP 409 Conflict (PostgreSQL row lock).")

# 14. Immutability Invariant & Rejection of Direct Modification
print("\n[CHECK 14] Finalized Result Immutability Invariant")
direct_edit_res = requests.post(
    f"{BASE_URL}/lab/order-items/{cbc_item['id']}/results",
    json={"value": "7.5", "abnormal_flag": "ABNORMAL"},
    headers=nurse_headers
)
assert direct_edit_res.status_code == 400
assert "finalized result already exists" in direct_edit_res.json()["detail"]
print("  PASS: Direct modification of finalized result strictly blocked with HTTP 400.")

# 15. Clinical Amendment Workflow & Patient Visibility Invariant
print("\n[CHECK 15] Versioned Clinical Amendment & Patient Visibility Invariant")
# Doctor 2 attempts amendment -> 403
res = requests.post(
    f"{BASE_URL}/lab/results/{result1_id}/amend",
    json={"value": "7.2", "amendment_reason": "Unauthorized amendment by Dr. Martinez"},
    headers=doc2_headers
)
assert res.status_code == 403
print("  PASS: Dr. Martinez (same department) blocked from amending Doctor Chen's result (403 Forbidden).")

# Doctor 1 amends result: creates v2 (FINAL), v1 becomes AMENDED
amend_payload = {
    "value": "7.2",
    "numeric_value": 7.2,
    "abnormal_flag": "CRITICAL",
    "amendment_reason": "Analyzer baseline recalibration applied per QA standard",
    "comments": "Recalibrated run confirmed by pathologist"
}
res = requests.post(f"{BASE_URL}/lab/results/{result1_id}/amend", json=amend_payload, headers=doc1_headers)
assert res.status_code == 200
amended_v2 = res.json()
v2_id = amended_v2["id"]
assert amended_v2["status"] == "FINAL"
assert amended_v2["parent_result_id"] == result1_id
assert amended_v2["value"] == "7.2"
print(f"  PASS: Created version 2 Result #{v2_id} (FINAL) referencing parent #{result1_id} [LAB_RESULT_AMENDED]")

# Check PostgreSQL directly for v1 preservation
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
cur.execute("SELECT id, status, value, amendment_reason FROM lab_results WHERE id = %s", (result1_id,))
v1_db = cur.fetchone()
assert v1_db[1] == "AMENDED"
assert v1_db[2] == "6.9", "Original clinical value '6.9' must remain permanently preserved!"
print("  PASS: PostgreSQL audit verification: v1 row preserved with status AMENDED and original value '6.9' untouched.")

# Patient View: MUST ONLY see current FINAL result (v2); obsolete AMENDED v1 MUST NOT be present
res = requests.get(f"{BASE_URL}/lab/patients/{pat_id}/results", headers=pat_headers)
assert res.status_code == 200
pat_results = res.json()
pat_res_ids = [r["id"] for r in pat_results]
assert v2_id in pat_res_ids, "Patient MUST receive current active FINAL result v2"
assert result1_id not in pat_res_ids, "Obsolete AMENDED v1 MUST NOT be exposed as an active result to the patient!"
print(f"  PASS: Patient receives only active FINAL result (v2); obsolete AMENDED result (v1) is shielded.")

# Doctor View: CAN view full historical version lineage (both v1 and v2)
res = requests.get(f"{BASE_URL}/lab/patients/{pat_id}/results", headers=doc1_headers)
assert res.status_code == 200
doc_results = res.json()
doc_res_ids = [r["id"] for r in doc_results]
assert v2_id in doc_res_ids, "Doctor should see current FINAL result v2"
assert result1_id in doc_res_ids, "Doctor should see preserved AMENDED result v1 for clinical audit history"
print("  PASS: Attending physician retains complete access to all historical result versions for clinical audit.")

# 16. Comprehensive Direct PostgreSQL Audit Verification (All 10 Events)
print("\n[CHECK 16] Direct PostgreSQL Verification of All 10 Clinical Audit Events")
expected_10_actions = [
    "LAB_ORDER_CREATED",
    "LAB_ORDER_CANCELLED",
    "LAB_SAMPLE_COLLECTED",
    "LAB_SAMPLE_RECEIVED",
    "LAB_SAMPLE_REJECTED",
    "LAB_PROCESSING_STARTED",
    "LAB_RESULT_ENTERED",
    "LAB_RESULT_VERIFIED",
    "LAB_RESULT_FINALIZED",
    "LAB_RESULT_AMENDED"
]

cur.execute("""
    SELECT action, user_id, resource_type, resource_id, created_at
    FROM audit_logs
    WHERE action IN %s
    ORDER BY id ASC
""", (tuple(expected_10_actions),))
audit_rows = cur.fetchall()

found_actions = {}
for action, user_id, resource_type, resource_id, created_at in audit_rows:
    assert user_id is not None, f"Audit event {action} missing actor (user_id)"
    assert resource_id is not None, f"Audit event {action} missing object reference (resource_id)"
    assert created_at is not None, f"Audit event {action} missing timestamp"
    found_actions[action] = {
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "created_at": str(created_at)
    }

print("\n  Verified Audit Events from PostgreSQL:")
print("  " + "-" * 70)
print(f"  {'ACTION':<25} | {'ACTOR (USER)':<12} | {'OBJECT REF':<14} | {'TIMESTAMP'}")
print("  " + "-" * 70)
for exp_action in expected_10_actions:
    assert exp_action in found_actions, f"BLOCKER: Audit trail missing required event: {exp_action}"
    info = found_actions[exp_action]
    print(f"  {exp_action:<25} | User #{info['user_id']:<6} | {info['resource_type']}:{info['resource_id']:<4} | {info['created_at']}")
print("  " + "-" * 70)
print(f"  PASS: All 10 required Step 4 clinical audit events verified directly in PostgreSQL audit_logs table.")

cur.close()
conn.close()

print("\n" + "=" * 75)
print("ALL 16 STEP 4 LABORATORY & DIAGNOSTICS AUDIT CHECKS PASSED PERFECTLY!")
print("=" * 75)
