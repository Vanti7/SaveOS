"""
Tests pour les actions de gestion d'un agent (Détails/Configurer/Supprimer,
voir web/app/agents/page.tsx) : GET/PATCH/DELETE /api/v1/agents/{agent_id}.
Couvre aussi la correction de la fuite du token (haché) dans les réponses de
listing/détail (api/schemas.py::AgentPublic, sans le champ token).
"""
import pytest

from api.database import Agent, Job, Snapshot, Tenant, User
from api.auth import AuthManager

DASHBOARD_TOKEN = "test-dashboard-token"


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_TOKEN", DASHBOARD_TOKEN)
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")


def _dashboard_headers():
    return {"Authorization": f"Bearer {DASHBOARD_TOKEN}"}


def _make_tenant(db_session, name):
    tenant = Tenant(name=name, registration_secret_hash=AuthManager.hash_token(f"secret-{name}"))
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _make_agent(db_session, tenant_id, hostname):
    agent = Agent(
        tenant_id=tenant_id,
        hostname=hostname,
        platform="linux",
        token=AuthManager.hash_token(f"token-for-{tenant_id}-{hostname}"),
        status="active",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def _make_user_headers(db_session, tenant_id, role="user"):
    user = User(
        tenant_id=tenant_id,
        email=f"user-{tenant_id}@test.local",
        role=role,
        password_hash=AuthManager.hash_password("test-password"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = AuthManager.create_access_token(user)
    return {"Authorization": f"Bearer {token}"}


# --- GET /api/v1/agents (listing) : plus de fuite du token ---

def test_list_agents_does_not_expose_token(client, db_session):
    tenant = _make_tenant(db_session, "tenant-list")
    _make_agent(db_session, tenant.id, "host-list")

    response = client.get("/api/v1/agents", headers=_dashboard_headers())
    assert response.status_code == 200
    assert all("token" not in a for a in response.json())


# --- GET /api/v1/agents/{agent_id} (Détails) ---

def test_get_agent_detail_as_dashboard(client, db_session):
    tenant = _make_tenant(db_session, "tenant-detail")
    agent = _make_agent(db_session, tenant.id, "host-detail")
    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    db_session.add(Snapshot(job_id=job.id, name="archive-1", repo_path="/repo", size_bytes=1234))
    db_session.commit()

    response = client.get(f"/api/v1/agents/{agent.id}", headers=_dashboard_headers())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["hostname"] == "host-detail"
    assert data["total_snapshots"] == 1
    assert data["total_size_bytes"] == 1234
    assert "token" not in data


def test_get_agent_detail_unknown_returns_404(client, db_session):
    response = client.get("/api/v1/agents/999999", headers=_dashboard_headers())
    assert response.status_code == 404


def test_get_agent_detail_cross_tenant_user_forbidden(client, db_session):
    tenant_a = _make_tenant(db_session, "tenant-a-detail")
    tenant_b = _make_tenant(db_session, "tenant-b-detail")
    agent_a = _make_agent(db_session, tenant_a.id, "host-a")
    headers_b = _make_user_headers(db_session, tenant_b.id)

    response = client.get(f"/api/v1/agents/{agent_a.id}", headers=headers_b)
    assert response.status_code == 403


def test_get_agent_detail_own_tenant_user_allowed(client, db_session):
    tenant = _make_tenant(db_session, "tenant-own-detail")
    agent = _make_agent(db_session, tenant.id, "host-own")
    headers = _make_user_headers(db_session, tenant.id)

    response = client.get(f"/api/v1/agents/{agent.id}", headers=headers)
    assert response.status_code == 200


# --- PATCH /api/v1/agents/{agent_id} (Configurer) ---

def test_update_agent_hostname(client, db_session):
    tenant = _make_tenant(db_session, "tenant-update")
    agent = _make_agent(db_session, tenant.id, "host-old")

    response = client.patch(
        f"/api/v1/agents/{agent.id}", json={"hostname": "host-new"}, headers=_dashboard_headers()
    )
    assert response.status_code == 200, response.text
    assert response.json()["hostname"] == "host-new"

    refreshed = client.get(f"/api/v1/agents/{agent.id}", headers=_dashboard_headers())
    assert refreshed.json()["hostname"] == "host-new"


def test_update_agent_hostname_conflict_within_tenant(client, db_session):
    tenant = _make_tenant(db_session, "tenant-conflict")
    _make_agent(db_session, tenant.id, "host-taken")
    agent_b = _make_agent(db_session, tenant.id, "host-b")

    response = client.patch(
        f"/api/v1/agents/{agent_b.id}", json={"hostname": "host-taken"}, headers=_dashboard_headers()
    )
    assert response.status_code == 409


def test_update_agent_cross_tenant_user_forbidden(client, db_session):
    tenant_a = _make_tenant(db_session, "tenant-a-update")
    tenant_b = _make_tenant(db_session, "tenant-b-update")
    agent_a = _make_agent(db_session, tenant_a.id, "host-a-update")
    headers_b = _make_user_headers(db_session, tenant_b.id)

    response = client.patch(
        f"/api/v1/agents/{agent_a.id}", json={"hostname": "renamed"}, headers=headers_b
    )
    assert response.status_code == 403


# --- DELETE /api/v1/agents/{agent_id} (Supprimer, cascade) ---

def test_delete_agent_cascades_jobs_and_snapshots(client, db_session):
    tenant = _make_tenant(db_session, "tenant-delete")
    agent = _make_agent(db_session, tenant.id, "host-delete")
    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    snapshot = Snapshot(job_id=job.id, name="archive-del", repo_path="/repo", size_bytes=42)
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    agent_id, snapshot_id = agent.id, snapshot.id

    response = client.delete(f"/api/v1/agents/{agent_id}", headers=_dashboard_headers())
    assert response.status_code == 204

    assert db_session.query(Agent).filter(Agent.id == agent_id).first() is None
    assert db_session.query(Job).filter(Job.agent_id == agent_id).first() is None
    assert db_session.query(Snapshot).filter(Snapshot.id == snapshot_id).first() is None


def test_delete_agent_nullifies_cross_agent_restore_reference(client, db_session):
    tenant = _make_tenant(db_session, "tenant-delete-cross")
    agent_source = _make_agent(db_session, tenant.id, "host-source")
    agent_other = _make_agent(db_session, tenant.id, "host-other")

    backup_job = Job(agent_id=agent_source.id, type="backup", status="completed")
    db_session.add(backup_job)
    db_session.commit()
    db_session.refresh(backup_job)
    snapshot = Snapshot(job_id=backup_job.id, name="archive-cross", repo_path="/repo", size_bytes=10)
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    # Job de restauration sur un AUTRE agent, référençant le snapshot produit
    # par agent_source (Job.snapshot_id) — cas réel : restaurer sur une autre
    # machine que celle d'origine.
    restore_job = Job(agent_id=agent_other.id, type="restore", status="completed", snapshot_id=snapshot.id)
    db_session.add(restore_job)
    db_session.commit()
    db_session.refresh(restore_job)

    response = client.delete(f"/api/v1/agents/{agent_source.id}", headers=_dashboard_headers())
    assert response.status_code == 204

    db_session.refresh(restore_job)
    assert restore_job.snapshot_id is None
    # Le job de restauration lui-même (sur agent_other, pas supprimé) survit.
    assert db_session.query(Job).filter(Job.id == restore_job.id).first() is not None


def test_delete_agent_unknown_returns_404(client, db_session):
    response = client.delete("/api/v1/agents/999999", headers=_dashboard_headers())
    assert response.status_code == 404


def test_delete_agent_cross_tenant_user_forbidden(client, db_session):
    tenant_a = _make_tenant(db_session, "tenant-a-delete")
    tenant_b = _make_tenant(db_session, "tenant-b-delete")
    agent_a = _make_agent(db_session, tenant_a.id, "host-a-delete")
    headers_b = _make_user_headers(db_session, tenant_b.id)

    response = client.delete(f"/api/v1/agents/{agent_a.id}", headers=headers_b)
    assert response.status_code == 403
    assert db_session.query(Agent).filter(Agent.id == agent_a.id).first() is not None
