import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.models import User, UserRole, Patient

def test_patient_cannot_access_other_patient_data(client, db_session):
    # Patient A
    ua = User(email="pat.a.rbac@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Alice", role=UserRole.PATIENT)
    db_session.add(ua)
    db_session.commit()
    pa = Patient(user_id=ua.id, address="Alice Home")
    db_session.add(pa)
    db_session.commit()

    # Patient B
    ub = User(email="pat.b.rbac@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Bob", role=UserRole.PATIENT)
    db_session.add(ub)
    db_session.commit()
    pb = Patient(user_id=ub.id, address="Bob Secret Home")
    db_session.add(pb)
    db_session.commit()

    token_a = create_access_token({"sub": str(ua.id), "role": "PATIENT"})

    # Patient A tries to access Patient B's profile: GET /api/v1/patients/{pb.id}
    res = client.get(
        f"/api/v1/patients/{pb.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    # MUST be rejected with 403 Forbidden!
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # Patient A can access their own profile
    res_own = client.get(
        f"/api/v1/patients/{pa.id}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_own.status_code == 200
    assert res_own.json()["full_name"] == "Alice"

def test_patient_cannot_access_admin_audit_logs(client, db_session):
    # Patient
    u = User(email="pat.audit@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Auditor", role=UserRole.PATIENT)
    # Admin
    u_admin = User(email="admin.audit@medicore.ai", hashed_password=get_password_hash("Admin@1234"), full_name="Admin Boss", role=UserRole.ADMIN)
    db_session.add_all([u, u_admin])
    db_session.commit()

    token_patient = create_access_token({"sub": str(u.id), "role": "PATIENT"})
    token_admin = create_access_token({"sub": str(u_admin.id), "role": "ADMIN"})

    # Patient tries to query audit logs -> 403 Forbidden
    res = client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token_patient}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # Admin can access audit logs -> 200 OK
    res_admin = client.get(
        "/api/v1/audit-logs",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert res_admin.status_code == 200


def test_unauthenticated_requests_are_strictly_rejected(client):
    """Test that requests lacking credentials receive HTTP 401 Unauthorized."""
    res = client.get("/api/v1/patients/1")
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers


def test_patient_cannot_query_other_patient_clinical_rag(client, db_session):
    """Test that AI Clinical RAG rejects cross-patient data access with HTTP 403."""
    ua = User(email="alice.rag@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Alice RAG", role=UserRole.PATIENT)
    ub = User(email="bob.rag@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Bob RAG", role=UserRole.PATIENT)
    db_session.add_all([ua, ub])
    db_session.commit()

    pa = Patient(user_id=ua.id)
    pb = Patient(user_id=ub.id)
    db_session.add_all([pa, pb])
    db_session.commit()

    token_a = create_access_token({"sub": str(ua.id), "role": "PATIENT"})

    # Patient A attempts to search Patient B's records via RAG endpoint
    res = client.post(
        "/api/v1/ai/rag/query",
        json={"patient_id": pb.id, "query": "heart condition"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]
