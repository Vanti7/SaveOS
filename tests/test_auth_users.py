"""
Tests pour la connexion (login), l'émission/vérification de JWT, et les
rôles appliqués (admin/user) — voir docs/adr/0005-gestion-utilisateurs-roles.md.
"""
import pytest

from api.database import Agent, Tenant
from api.auth import AuthManager

DASHBOARD_TOKEN = "test-dashboard-token"


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_TOKEN", DASHBOARD_TOKEN)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")


def _dashboard_headers():
    return {"Authorization": f"Bearer {DASHBOARD_TOKEN}"}


def _user_headers(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Connexion ---

def test_login_success(client, test_admin):
    user, password = test_admin
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == user.email
    assert "password_hash" not in data["user"]


def test_login_wrong_password(client, test_admin):
    user, _ = test_admin
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post("/api/v1/auth/login", json={"email": "nobody@test.local", "password": "x"})
    assert response.status_code == 401


def test_jwt_authenticates_subsequent_request(client, test_admin):
    user, password = test_admin
    headers = _user_headers(client, user.email, password)

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_auth_me_rejects_agent_and_dashboard_token(client, test_agent):
    agent, token = test_agent
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

    response = client.get("/api/v1/auth/me", headers=_dashboard_headers())
    assert response.status_code == 401


# --- Isolation par tenant pour un utilisateur connecté ---

def test_user_cannot_list_another_tenant(client, db_session, test_user):
    user, password = test_user
    other_tenant = Tenant(name="other-tenant", registration_secret_hash=AuthManager.hash_token("other-secret"))
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    headers = _user_headers(client, user.email, password)
    response = client.get(f"/api/v1/agents?tenant_id={other_tenant.id}", headers=headers)
    assert response.status_code == 403


def test_user_list_own_tenant_ignoring_explicit_match(client, db_session, test_user):
    user, password = test_user
    agent = Agent(
        tenant_id=user.tenant_id, hostname="own-host", platform="linux",
        token=AuthManager.hash_token("own-agent-token"), status="active",
    )
    db_session.add(agent)
    db_session.commit()

    headers = _user_headers(client, user.email, password)
    response = client.get(f"/api/v1/agents?tenant_id={user.tenant_id}", headers=headers)
    assert response.status_code == 200
    assert [a["hostname"] for a in response.json()] == ["own-host"]


def test_dashboard_token_can_still_list_any_tenant(client, test_agent):
    agent, _ = test_agent
    response = client.get(f"/api/v1/agents?tenant_id={agent.tenant_id}", headers=_dashboard_headers())
    assert response.status_code == 200


# --- Gestion des utilisateurs ---

def test_create_user_bootstrap_via_dashboard_requires_tenant_id(client, db_session):
    tenant = Tenant(name="bootstrap-tenant", registration_secret_hash=AuthManager.hash_token("bootstrap-secret"))
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    response = client.post(
        "/api/v1/users",
        json={"email": "first-admin@test.local", "password": "x", "role": "admin"},
        headers=_dashboard_headers(),
    )
    assert response.status_code == 422

    response = client.post(
        f"/api/v1/users?tenant_id={tenant.id}",
        json={"email": "first-admin@test.local", "password": "x", "role": "admin"},
        headers=_dashboard_headers(),
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant.id


def test_admin_creates_user_in_own_tenant(client, test_admin):
    admin, password = test_admin
    headers = _user_headers(client, admin.email, password)

    response = client.post(
        "/api/v1/users",
        json={"email": "teammate@test.local", "password": "x"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == admin.tenant_id
    assert response.json()["role"] == "user"


def test_admin_cannot_create_user_in_another_tenant(client, db_session, test_admin):
    admin, password = test_admin
    other_tenant = Tenant(name="other-tenant-2", registration_secret_hash=AuthManager.hash_token("other-secret-2"))
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    headers = _user_headers(client, admin.email, password)
    response = client.post(
        f"/api/v1/users?tenant_id={other_tenant.id}",
        json={"email": "intruder@test.local", "password": "x"},
        headers=headers,
    )
    assert response.status_code == 403


def test_non_admin_user_cannot_create_users(client, test_user):
    user, password = test_user
    headers = _user_headers(client, user.email, password)

    response = client.post("/api/v1/users", json={"email": "x@test.local", "password": "x"}, headers=headers)
    assert response.status_code == 403


# --- provision_agent ouvert aux admins de tenant ---

def test_admin_can_provision_agent_for_own_tenant(client, test_admin):
    admin, password = test_admin
    headers = _user_headers(client, admin.email, password)

    response = client.post(
        "/api/v1/agents/provision",
        params={"hostname": "admin-host", "platform": "linux", "tenant_id": admin.tenant_id},
        headers=headers,
    )
    assert response.status_code == 200


def test_admin_cannot_provision_agent_for_another_tenant(client, db_session, test_admin):
    admin, password = test_admin
    other_tenant = Tenant(name="other-tenant-3", registration_secret_hash=AuthManager.hash_token("other-secret-3"))
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    headers = _user_headers(client, admin.email, password)
    response = client.post(
        "/api/v1/agents/provision",
        params={"hostname": "intruder-host", "platform": "linux", "tenant_id": other_tenant.id},
        headers=headers,
    )
    assert response.status_code == 403


# --- Gestion des tenants reste réservée au token dashboard ---

def test_admin_cannot_create_tenant(client, test_admin):
    admin, password = test_admin
    headers = _user_headers(client, admin.email, password)

    response = client.post("/api/v1/tenants", json={"name": "new-tenant"}, headers=headers)
    assert response.status_code == 403


def test_admin_cannot_list_tenants(client, test_admin):
    admin, password = test_admin
    headers = _user_headers(client, admin.email, password)

    response = client.get("/api/v1/tenants", headers=headers)
    assert response.status_code == 403
