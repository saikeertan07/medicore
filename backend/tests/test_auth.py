import pytest
from app.core.security import get_password_hash
from app.models.models import User, UserRole, Patient

def test_login_success_and_failure(client, db_session):
    # Active user
    u = User(
        email="active.user@medicore.ai",
        hashed_password=get_password_hash("ValidPass@123"),
        full_name="Active User",
        role=UserRole.PATIENT,
        is_active=True
    )
    # Inactive user
    u_inactive = User(
        email="inactive.user@medicore.ai",
        hashed_password=get_password_hash("ValidPass@123"),
        full_name="Inactive User",
        role=UserRole.PATIENT,
        is_active=False
    )
    db_session.add_all([u, u_inactive])
    db_session.commit()

    # 1. Valid login
    res = client.post("/api/v1/auth/login", json={
        "email": "active.user@medicore.ai",
        "password": "ValidPass@123"
    })
    assert res.status_code == 200
    token_data = res.json()
    assert "access_token" in token_data
    assert token_data["role"] == "PATIENT"

    # 2. Invalid password -> 401 Unauthorized
    res_bad = client.post("/api/v1/auth/login", json={
        "email": "active.user@medicore.ai",
        "password": "WrongPassword@123"
    })
    assert res_bad.status_code == 401

    # 3. Inactive account -> 403 Forbidden
    res_inactive = client.post("/api/v1/auth/login", json={
        "email": "inactive.user@medicore.ai",
        "password": "ValidPass@123"
    })
    assert res_inactive.status_code == 403
    assert "inactive" in res_inactive.json()["detail"].lower()

def test_registration_and_password_policy(client, db_session):
    # 1. Weak password (too short) -> 400 Bad Request
    res_weak = client.post("/api/v1/auth/register", json={
        "email": "new.user@medicore.ai",
        "full_name": "New User",
        "password": "sh"
    })
    assert res_weak.status_code == 400

    # 2. Valid registration -> 201 Created
    res_reg = client.post("/api/v1/auth/register", json={
        "email": "brandnew.user@medicore.ai",
        "full_name": "Brand New",
        "password": "SecurePassword@123"
    })
    assert res_reg.status_code == 201
    assert "access_token" in res_reg.json()
    assert res_reg.json()["role"] == "PATIENT"

def test_admin_user_provisioning_and_status(client, db_session):
    admin = User(
        email="super.admin@medicore.ai",
        hashed_password=get_password_hash("AdminPass@123"),
        full_name="Super Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": "super.admin@medicore.ai",
        "password": "AdminPass@123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Admin provisions a staff account
    create_res = client.post("/api/v1/auth/users", headers=headers, json={
        "email": "staff.member@medicore.ai",
        "password": "StaffPassword@123",
        "full_name": "Nurse Joy",
        "role": "STAFF",
        "phone": "555-9000"
    })
    assert create_res.status_code == 201
    staff_data = create_res.json()
    assert staff_data["role"] == "STAFF"
    assert staff_data["is_active"] is True
    staff_id = staff_data["id"]

    # Toggle status to inactive
    toggle_res = client.patch(f"/api/v1/auth/users/{staff_id}/status", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # Inactive staff cannot login
    staff_login = client.post("/api/v1/auth/login", json={
        "email": "staff.member@medicore.ai",
        "password": "StaffPassword@123"
    })
    assert staff_login.status_code == 403


def test_refresh_token_rotation_and_revocation(client, db_session):
    u = User(
        email="refresh.test@medicore.ai",
        hashed_password=get_password_hash("ValidPass@123"),
        full_name="Refresh Tester",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db_session.add(u)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": "refresh.test@medicore.ai",
        "password": "ValidPass@123"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    old_refresh_token = data["refresh_token"]

    # 1. Successful refresh
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert ref_res.status_code == 200
    new_data = ref_res.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    new_access_token = new_data["access_token"]
    new_refresh_token = new_data["refresh_token"]

    # 2. Access /me with new access token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh.test@medicore.ai"

    # 3. Old refresh token was rotated and revoked -> reuse attempt fails with 401
    reuse_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert reuse_res.status_code == 401


def test_logout_invalidates_session(client, db_session):
    u = User(
        email="logout.test@medicore.ai",
        hashed_password=get_password_hash("ValidPass@123"),
        full_name="Logout Tester",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add(u)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": "logout.test@medicore.ai",
        "password": "ValidPass@123"
    })
    access_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Verify session is valid before logout
    me_before = client.get("/api/v1/auth/me", headers=headers)
    assert me_before.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert "revoked" in logout_res.json()["message"].lower()

    # Re-accessing endpoint with the revoked token must fail with 401
    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower() or "terminated" in me_after.json()["detail"].lower()


def test_login_brute_force_throttling(client, db_session):
    u = User(
        email="brute.force@medicore.ai",
        hashed_password=get_password_hash("ValidPass@123"),
        full_name="Brute Force Target",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add(u)
    db_session.commit()

    # Send 5 incorrect attempts
    for _ in range(5):
        fail_res = client.post("/api/v1/auth/login", json={
            "email": "brute.force@medicore.ai",
            "password": "WrongPassword!"
        })
        assert fail_res.status_code == 401

    # 6th attempt should be blocked with 429 Too Many Requests
    blocked_res = client.post("/api/v1/auth/login", json={
        "email": "brute.force@medicore.ai",
        "password": "ValidPass@123"
    })
    assert blocked_res.status_code == 429
    assert "throttled" in blocked_res.json()["detail"].lower()


