import sys
import os
import requests
import psycopg2
from datetime import datetime, date, timedelta

BASE_URL = "http://localhost:8000/api/v1"
DB_URL = "postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db"

print("=" * 70)
print("MEDICORE AI — STEP 3 LIVE POSTGRESQL & CLINICAL WORKFLOW VERIFICATION")
print("=" * 70)

# Helper function to login
def login(email, password):
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise Exception(f"Login failed for {email}: {res.status_code} - {res.text}")
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. Health check
print("\n[CHECK 1] System & PostgreSQL Health Check")
res = requests.get(f"{BASE_URL}/health")
assert res.status_code == 200, f"Health failed: {res.text}"
health_data = res.json()
assert health_data["database"] == "healthy"
assert health_data["database_engine"] == "postgresql"
print(f"  PASS: Backend reports healthy PostgreSQL engine ({health_data['environment']})")

# 2. Login as Receptionist and register patient
print("\n[CHECK 2] Receptionist: Login & Register Patient")
rec_headers = login("receptionist@medicore.ai", "Reception@123")
reg_payload = {
    "full_name": f"Clinical Walkin {int(datetime.utcnow().timestamp())}",
    "email": f"walkin_{int(datetime.utcnow().timestamp())}@example.com",
    "phone": f"+1555{int(datetime.utcnow().timestamp()) % 1000000:06d}",
    "date_of_birth": "1988-04-12",
    "gender": "Female",
    "blood_group": "B+"
}
res = requests.post(f"{BASE_URL}/patients", json=reg_payload, headers=rec_headers)
assert res.status_code == 201, f"Register failed: {res.text}"
patient = res.json()
patient_id = patient["id"]
patient_number = patient["patient_number"]
print(f"  PASS: Registered Patient #{patient_id} ({patient_number}: {patient['full_name']})")

# 3. Book appointment and check in
print("\n[CHECK 3] Receptionist: Book Appointment & Check In")
# Fetch doctor 1 (Dr. Marcus Vance, ID 1)
doc_res = requests.get(f"{BASE_URL}/doctors/1")
doc = doc_res.json()
today_str = date.today().isoformat()

# Get slots
slots_res = requests.get(f"{BASE_URL}/appointments/available-slots?doctor_id=1&date={today_str}")
slots = slots_res.json()["slots"]
avail_slot = next((s for s in slots if s["is_available"]), None)
if not avail_slot:
    # If today's slots are filled or passed, pick tomorrow
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    slots_res = requests.get(f"{BASE_URL}/appointments/available-slots?doctor_id=1&date={tomorrow_str}")
    target_date = tomorrow_str
    avail_slot = next(s for s in slots_res.json()["slots"] if s["is_available"])
else:
    target_date = today_str

book_payload = {
    "patient_id": patient_id,
    "doctor_id": 1,
    "department_id": doc["department_id"],
    "date": target_date,
    "start_time": avail_slot["start_time"],
    "end_time": avail_slot["end_time"],
    "type": "IN_PERSON",
    "reason": "Severe migratory polyarthritis and recurrent fevers."
}
res = requests.post(f"{BASE_URL}/appointments", json=book_payload, headers=rec_headers)
assert res.status_code == 201, f"Booking failed: {res.text}"
appt = res.json()
appt_id = appt["id"]
print(f"  PASS: Booked Appointment #{appt_id} ({appt['appointment_number']})")

# Check in appointment
checkin_res = requests.post(f"{BASE_URL}/appointments/{appt_id}/check-in", json={"notes": "Patient arrived at reception triage desk."}, headers=rec_headers)
assert checkin_res.status_code == 200
assert checkin_res.json()["status"] == "CHECKED_IN"
print(f"  PASS: Checked in patient for appointment #{appt_id}")

# 4. Nurse opens encounter & records vitals
print("\n[CHECK 4] Nurse: Open Encounter & Record Vitals Intake")
nurse_headers = login("nurse.sarah@medicore.ai", "Nurse@123")

# Create encounter
enc_payload = {
    "patient_id": patient_id,
    "appointment_id": appt_id,
    "attending_doctor_id": 1,
    "department_id": doc["department_id"],
    "encounter_type": "OUTPATIENT"
}
res = requests.post(f"{BASE_URL}/encounters", json=enc_payload, headers=nurse_headers)
assert res.status_code == 201, f"Encounter creation failed: {res.text}"
enc = res.json()
enc_id = enc["id"]
enc_number = enc["encounter_number"]
print(f"  PASS: Primary Encounter created #{enc_id} ({enc_number})")

# Verify partial unique constraint: Duplicate encounter for same appointment must return 409
dup_res = requests.post(f"{BASE_URL}/encounters", json=enc_payload, headers=nurse_headers)
assert dup_res.status_code == 409, f"Expected 409 duplicate conflict, got: {dup_res.status_code}"
print(f"  PASS: Duplicate encounter creation for appointment rejected with HTTP 409")

# Record Vitals
vitals_payload = {
    "temperature_c": 38.1,
    "heart_rate": 88,
    "respiratory_rate": 18,
    "systolic_bp": 128,
    "diastolic_bp": 82,
    "oxygen_saturation": 98.0,
    "height_cm": 168.0,
    "weight_kg": 64.0,
    "pain_score": 4,
    "notes": "Patient reports moderate pain in both wrists and right knee."
}
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/vitals", json=vitals_payload, headers=nurse_headers)
assert res.status_code == 201, f"Vitals recording failed: {res.text}"
vitals_data = res.json()
# Expected BMI: 64 / (1.68^2) = 22.68 -> 22.7
assert vitals_data["bmi"] == 22.7
print(f"  PASS: Vitals recorded successfully (BMI auto-calculated: {vitals_data['bmi']})")

# Nurse starts encounter
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/start", headers=nurse_headers)
assert res.status_code == 200
assert res.json()["status"] == "IN_PROGRESS"
print(f"  PASS: Encounter transitioned to IN_PROGRESS")

# 5. Doctor opens workspace, writes SOAP note, adds diagnosis, finalizes
print("\n[CHECK 5] Doctor: SOAP Clinical Note, Diagnoses, Treatment Plan & Finalization")
doc_headers = login("doctor.chen@medicore.ai", "Doctor@123")

# Doctor creates SOAP draft
soap_payload = {
    "chief_complaint": "Polyarticular joint pain with morning stiffness lasting over an hour.",
    "history_of_present_illness": "Symptoms commenced 4 weeks ago. Initially bilateral MCP joints, now extending to knees.",
    "symptoms": "Low-grade fever (38.1 C on triage), fatigue, morning stiffness.",
    "examination_findings": "Bilateral MCP swelling with tenderness. Right knee mild effusion.",
    "clinical_assessment": "Seropositive Rheumatoid Arthritis (Early presentation).",
    "differential_diagnosis": "Systemic Lupus Erythematosus, Parvovirus B19 reactive arthropathy.",
    "treatment_plan": "Initiate Methotrexate 15mg weekly with Folic Acid 5mg. NSAID for symptomatic relief.",
    "patient_instructions": "Monitor for gastrointestinal intolerance. Avoid alcohol during therapy.",
    "follow_up_instructions": "Return in 4 weeks for baseline LFT/CBC and rheumatology evaluation.",
    "follow_up_date": (date.today() + timedelta(days=28)).isoformat()
}
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/clinical-notes", json=soap_payload, headers=doc_headers)
assert res.status_code == 201, f"SOAP note creation failed: {res.text}"
note = res.json()
note_id = note["id"]
assert note["status"] == "DRAFT"
assert note["version"] == 1
print(f"  PASS: Doctor drafted SOAP note #{note_id} (Version 1, DRAFT)")

# Doctor records structured diagnosis
diag_payload = {
    "name": "Seropositive rheumatoid arthritis",
    "code": "M05.9",
    "code_system": "ICD-10",
    "type": "PRIMARY",
    "notes": "Early erosive joint changes suspected; inflammatory markers elevated."
}
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/diagnoses", json=diag_payload, headers=doc_headers)
assert res.status_code == 201, f"Diagnosis creation failed: {res.text}"
diag = res.json()
print(f"  PASS: Recorded Primary Diagnosis #{diag['id']} ({diag['name']} [{diag['code']}])")

# Doctor finalizes clinical note
res = requests.post(f"{BASE_URL}/clinical-notes/{note_id}/finalize", headers=doc_headers)
assert res.status_code == 200, f"Finalization failed: {res.text}"
assert res.json()["status"] == "FINAL"
print(f"  PASS: Clinical note #{note_id} finalized and locked")

# Direct PUT on finalized note MUST fail
res = requests.put(f"{BASE_URL}/clinical-notes/{note_id}", json={"chief_complaint": "Illegal modification"}, headers=doc_headers)
assert res.status_code == 400, f"Expected 400 on modifying final note, got {res.status_code}"
print(f"  PASS: Direct modification of finalized note rejected with HTTP 400")

# Doctor authors versioned amendment
amend_payload = {
    "amendment_reason": "Baseline chest X-ray ordered prior to commencing DMARD therapy.",
    "treatment_plan": "Initiate Methotrexate 15mg weekly, Folic Acid 5mg, baseline CXR requested."
}
res = requests.post(f"{BASE_URL}/clinical-notes/{note_id}/amend", json=amend_payload, headers=doc_headers)
assert res.status_code == 201, f"Amendment failed: {res.text}"
amended_note = res.json()
assert amended_note["version"] == 2
assert amended_note["parent_note_id"] == note_id
print(f"  PASS: Clinical amendment version {amended_note['version']} created (Parent: #{amended_note['parent_note_id']})")

# Complete encounter
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/complete", headers=doc_headers)
assert res.status_code == 200
assert res.json()["status"] == "COMPLETED"
print(f"  PASS: Encounter #{enc_id} marked COMPLETED")

# 6. Patient Longitudinal Clinical Records View
print("\n[CHECK 6] Patient: Longitudinal Clinical History Access")
pat_headers = login("patient.sarah@medicore.ai", "Patient@123")
# Clinical timeline for patient 1 (Sarah)
res = requests.get(f"{BASE_URL}/patients/1/clinical-timeline", headers=pat_headers)
assert res.status_code == 200, f"Timeline fetch failed: {res.text}"
timeline = res.json()
print(f"  PASS: Patient successfully retrieved {len(timeline)} timeline entries")

# 7. Security & IDOR Attack Verification
print("\n[CHECK 7] Security & RBAC Access Boundary Checks")

# 7a. Receptionist -> Clinical Timeline -> MUST BE 403
res = requests.get(f"{BASE_URL}/patients/{patient_id}/clinical-timeline", headers=rec_headers)
assert res.status_code == 403, f"Expected 403 for receptionist clinical timeline, got {res.status_code}"
print("  PASS: Receptionist blocked from clinical timeline (HTTP 403)")

# 7b. Receptionist -> Vitals -> MUST BE 403
res = requests.get(f"{BASE_URL}/encounters/{enc_id}/vitals", headers=rec_headers)
assert res.status_code == 403, f"Expected 403 for receptionist vitals, got {res.status_code}"
print("  PASS: Receptionist blocked from clinical vitals (HTTP 403)")

# 7c. Receptionist -> Clinical Notes -> MUST BE 403
res = requests.get(f"{BASE_URL}/encounters/{enc_id}/clinical-notes", headers=rec_headers)
assert res.status_code == 403, f"Expected 403 for receptionist clinical notes, got {res.status_code}"
print("  PASS: Receptionist blocked from clinical notes (HTTP 403)")

# 7d. Nurse -> Create Doctor Clinical Note -> MUST BE 403
res = requests.post(f"{BASE_URL}/encounters/{enc_id}/clinical-notes", json={"chief_complaint": "Nurse note"}, headers=nurse_headers)
assert res.status_code == 403, f"Expected 403 for nurse creating doctor note, got {res.status_code}"
print("  PASS: Nurse blocked from authoring doctor clinical notes (HTTP 403)")

# 7e. Patient A -> Patient B Timeline -> MUST BE 403 (IDOR)
res = requests.get(f"{BASE_URL}/patients/{patient_id}/clinical-timeline", headers=pat_headers)
assert res.status_code == 403, f"Expected 403 for cross-patient timeline IDOR, got {res.status_code}"
print("  PASS: Cross-patient clinical timeline IDOR blocked (HTTP 403)")

# 7f. Same-Department Doctor Isolation (Dr. Martinez in Cardiology -> Dr. Chen's encounter)
print("\n[CHECK 7f] Same-Department Doctor Isolation (Dr. Martinez -> Dr. Chen's Encounter)")
doc2_headers = login("doctor.martinez@medicore.ai", "Doctor@123")

res_enc2 = requests.get(f"{BASE_URL}/encounters/{enc_id}", headers=doc2_headers)
assert res_enc2.status_code == 403, f"Expected 403 for same-department doctor viewing encounter, got {res_enc2.status_code}"
print("  PASS: Doctor B blocked from viewing Doctor A's encounter (HTTP 403)")

res_vit2 = requests.get(f"{BASE_URL}/encounters/{enc_id}/vitals", headers=doc2_headers)
assert res_vit2.status_code == 403, f"Expected 403 for same-department doctor viewing vitals, got {res_vit2.status_code}"
print("  PASS: Doctor B blocked from viewing Doctor A's encounter vitals (HTTP 403)")

res_notes2 = requests.get(f"{BASE_URL}/encounters/{enc_id}/clinical-notes", headers=doc2_headers)
assert res_notes2.status_code == 403, f"Expected 403 for same-department doctor viewing clinical notes, got {res_notes2.status_code}"
print("  PASS: Doctor B blocked from viewing Doctor A's clinical notes (HTTP 403)")

res_diag2 = requests.post(f"{BASE_URL}/encounters/{enc_id}/diagnoses", json={"name": "Hacked", "code": "Z00", "type": "PRIMARY"}, headers=doc2_headers)
assert res_diag2.status_code == 403, f"Expected 403 for same-department doctor adding diagnosis, got {res_diag2.status_code}"
print("  PASS: Doctor B blocked from creating diagnosis on Doctor A's encounter (HTTP 403)")

res_time2 = requests.get(f"{BASE_URL}/patients/{patient_id}/clinical-timeline", headers=doc2_headers)
assert res_time2.status_code == 403, f"Expected 403 for non-attending doctor viewing timeline, got {res_time2.status_code}"
print("  PASS: Non-attending doctor blocked from patient clinical timeline (HTTP 403)")

# 7g. Vitals Authoring Permissions (Admin blocked from recording/updating vitals)
print("\n[CHECK 7g] Vitals Authoring Security (Admin removal)")
admin_headers = login("admin@medicore.ai", "Admin@123")
res_adm_vit = requests.post(f"{BASE_URL}/encounters/{enc_id}/vitals", json={"heart_rate": 70}, headers=admin_headers)
assert res_adm_vit.status_code == 403, f"Expected 403 for admin recording vitals, got {res_adm_vit.status_code}"
print("  PASS: Admin blocked from recording vitals (HTTP 403)")

vit_id = vitals_data["id"]
res_adm_put = requests.put(f"{BASE_URL}/vitals/{vit_id}", json={"heart_rate": 72}, headers=admin_headers)
assert res_adm_put.status_code == 403, f"Expected 403 for admin updating vitals, got {res_adm_put.status_code}"
print("  PASS: Admin blocked from updating vitals (HTTP 403)")

# 7h. Encounter Creation RBAC (Receptionist, Staff, Admin blocked from POST /encounters)
print("\n[CHECK 7h] Encounter Creation RBAC Restrictions")
dummy_payload = {
    "patient_id": patient_id,
    "attending_doctor_id": 1,
    "department_id": doc["department_id"],
    "encounter_type": "WALK_IN"
}
res_rec_enc = requests.post(f"{BASE_URL}/encounters", json=dummy_payload, headers=rec_headers)
assert res_rec_enc.status_code == 403, f"Expected 403 for receptionist creating encounter, got {res_rec_enc.status_code}"
print("  PASS: Receptionist blocked from POST /encounters (HTTP 403)")

res_adm_enc = requests.post(f"{BASE_URL}/encounters", json=dummy_payload, headers=admin_headers)
assert res_adm_enc.status_code == 403, f"Expected 403 for admin creating encounter, got {res_adm_enc.status_code}"
print("  PASS: Admin blocked from POST /encounters (HTTP 403)")


# 8. Direct PostgreSQL Records & Audit Verification
print("\n[CHECK 8] Direct PostgreSQL Database & Audit Verification")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Check encounters table
cur.execute("SELECT id, encounter_number, status, encounter_type FROM encounters WHERE id = %s;", (enc_id,))
enc_row = cur.fetchone()
assert enc_row is not None
print(f"  PASS: PostgreSQL encounters table verified: ID={enc_row[0]}, Number={enc_row[1]}, Status={enc_row[2]}")

# Check encounter_vitals table
cur.execute("SELECT id, temperature_c, heart_rate, bmi FROM encounter_vitals WHERE encounter_id = %s;", (enc_id,))
vit_row = cur.fetchone()
assert vit_row is not None
print(f"  PASS: PostgreSQL encounter_vitals verified: Temp={vit_row[1]} C, HR={vit_row[2]}, BMI={vit_row[3]}")

# Check clinical_notes table
cur.execute("SELECT id, status, version, parent_note_id FROM clinical_notes WHERE encounter_id = %s ORDER BY version;", (enc_id,))
notes_rows = cur.fetchall()
assert len(notes_rows) == 2
assert notes_rows[0][1] == "AMENDED" and notes_rows[0][2] == 1
assert notes_rows[1][1] == "FINAL" and notes_rows[1][2] == 2 and notes_rows[1][3] == notes_rows[0][0]
print(f"  PASS: PostgreSQL clinical_notes versioning verified (v1 AMENDED -> v2 FINAL, parent={notes_rows[1][3]})")

# Check clinical_diagnoses table
cur.execute("SELECT id, name, code, type FROM clinical_diagnoses WHERE encounter_id = %s;", (enc_id,))
diag_row = cur.fetchone()
assert diag_row is not None
print(f"  PASS: PostgreSQL clinical_diagnoses verified: {diag_row[1]} [{diag_row[2]}] ({diag_row[3]})")

# Check Audit Logs
cur.execute("""
    SELECT action, resource_type, count(*) 
    FROM audit_logs 
    WHERE action IN ('ENCOUNTER_CREATE', 'ENCOUNTER_START', 'ENCOUNTER_COMPLETE', 'VITALS_CREATE', 'CLINICAL_NOTE_CREATE', 'CLINICAL_NOTE_FINALIZE', 'CLINICAL_NOTE_AMEND', 'DIAGNOSIS_CREATE')
    GROUP BY action, resource_type;
""")
audit_summary = cur.fetchall()
assert len(audit_summary) >= 7
print(f"  PASS: PostgreSQL audit_logs verified: {len(audit_summary)} clinical action types recorded")
for a in audit_summary:
    print(f"        - {a[0]} ({a[1]}): {a[2]} events")

cur.close()
conn.close()

print("\n" + "=" * 70)
print("ALL LIVE STEP 3 POSTGRESQL & CLINICAL VERIFICATION CHECKS PASSED!")
print("=" * 70)
