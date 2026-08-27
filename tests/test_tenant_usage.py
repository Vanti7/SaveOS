"""
Tests pour GET/PATCH /api/v1/tenants/{tenant_id} : consommation de quota,
coût estimé, ajustement du quota/rétention — voir
docs/adr/0006-facturation-quotas.md.
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from api.database import Agent, Job, Snapshot, Tenant
from api.auth import AuthManager
from api.main import compute_tenant_consumed_bytes

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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_usage(db_session, tenant_id, size_bytes):
    agent = Agent(
        tenant_id=tenant_id, hostname=f"host-{tenant_id}-{size_bytes}", platform="linux",
        token=AuthManager.hash_token(f"token-{tenant_id}-{size_bytes}"), status="active",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)

    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    db_session.add(Snapshot(job_id=job.id, name="snap", repo_path="/x", size_bytes=size_bytes))
    db_session.commit()


# --- GET /api/v1/tenants/{tenant_id} ---

def test_get_tenant_usage_computes_used_bytes_and_percent(client, db_session, test_admin):
    admin, password = test_admin
    tenant = db_session.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
    tenant.quota_bytes = 1000
    db_session.commit()
    _seed_usage(db_session, tenant.id, 250)

    headers = _user_headers(client, admin.email, password)
    response = client.get(f"/api/v1/tenants/{tenant.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["used_bytes"] == 250
    assert data["quota_percent"] == 25.0
    assert data["estimated_cost"] >= 0


def test_compute_tenant_consumed_bytes_returns_plain_int_from_decimal_scalar():
    """PostgreSQL renvoie SUM() sur une colonne BigInteger comme numeric,
    mappé par SQLAlchemy en decimal.Decimal — contrairement à SQLite
    (utilisé par tous les autres tests de ce fichier), qui renvoie un int
    directement. Sans int(...) explicite dans compute_tenant_consumed_bytes,
    TenantUsageResponse.estimated_cost (Decimal * float) lève TypeError en
    conditions réelles, jamais détecté par la suite de tests (SQLite)."""
    fake_db = MagicMock()
    fake_db.query.return_value.join.return_value.join.return_value.filter.return_value.scalar.return_value = Decimal('250')

    result = compute_tenant_consumed_bytes(fake_db, tenant_id=1)

    assert result == 250
    assert isinstance(result, int)


def test_get_tenant_usage_rejects_other_tenant_for_user(client, db_session, test_admin):
    admin, password = test_admin
    other_tenant = Tenant(name="other", registration_secret_hash=AuthManager.hash_token("other-secret"))
    db_session.add(other_tenant)
    db_session.commit()
    db_session.refresh(other_tenant)

    headers = _user_headers(client, admin.email, password)
    response = client.get(f"/api/v1/tenants/{other_tenant.id}", headers=headers)
    assert response.status_code == 403


def test_get_tenant_usage_dashboard_token_can_view_any_tenant(client, db_session, test_admin):
    admin, _ = test_admin
    response = client.get(f"/api/v1/tenants/{admin.tenant_id}", headers=_dashboard_headers())
    assert response.status_code == 200


def test_get_tenant_usage_unknown_tenant_returns_404(client):
    response = client.get("/api/v1/tenants/999999", headers=_dashboard_headers())
    assert response.status_code == 404


# --- PATCH /api/v1/tenants/{tenant_id} ---

def test_patch_tenant_updates_quota_with_dashboard_token(client, db_session, test_admin):
    admin, _ = test_admin
    response = client.patch(
        f"/api/v1/tenants/{admin.tenant_id}", json={"quota_bytes": 5000},
        headers=_dashboard_headers(),
    )
    assert response.status_code == 200
    assert response.json()["quota_bytes"] == 5000


def test_patch_tenant_rejects_admin_without_dashboard_token(client, test_admin):
    admin, password = test_admin
    headers = _user_headers(client, admin.email, password)
    response = client.patch(f"/api/v1/tenants/{admin.tenant_id}", json={"quota_bytes": 5000}, headers=headers)
    assert response.status_code == 403


def test_patch_tenant_unknown_tenant_returns_404(client):
    response = client.patch("/api/v1/tenants/999999", json={"quota_bytes": 5000}, headers=_dashboard_headers())
    assert response.status_code == 404
