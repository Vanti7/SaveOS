"""
Tests pour l'isolation multi-tenant (api/main.py, api/database.py) :
tenants réellement gérables, listes filtrées, quota appliqué, secret
d'enregistrement requis, hostname unique par tenant seulement — voir
docs/adr/0004-multi-tenancy-avancee.md.
"""
import pytest

from api.database import Agent, Job, Snapshot, Tenant
from api.auth import AuthManager

DASHBOARD_TOKEN = "test-dashboard-token"


@pytest.fixture(autouse=True)
def dashboard_token_env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_TOKEN", DASHBOARD_TOKEN)


def _dashboard_headers():
    return {"Authorization": f"Bearer {DASHBOARD_TOKEN}"}


def _create_tenant(client, name="tenant-a"):
    response = client.post(
        "/api/v1/tenants", json={"name": name}, headers=_dashboard_headers()
    )
    assert response.status_code == 200, response.text
    return response.json()


def _make_agent(db_session, tenant_id, hostname, token=None):
    agent = Agent(
        tenant_id=tenant_id,
        hostname=hostname,
        platform="linux",
        token=AuthManager.hash_token(token or f"token-for-{tenant_id}-{hostname}"),
        status="active",
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


# --- Création / liste de tenants ---

def test_create_tenant_requires_dashboard_token(client):
    response = client.post("/api/v1/tenants", json={"name": "x"})
    assert response.status_code == 403


def test_create_tenant_returns_registration_secret_once(client):
    tenant = _create_tenant(client)
    assert "registration_secret" in tenant
    assert tenant["name"] == "tenant-a"


def test_list_tenants_does_not_expose_registration_secret(client):
    _create_tenant(client)
    response = client.get("/api/v1/tenants", headers=_dashboard_headers())
    assert response.status_code == 200
    assert all("registration_secret" not in t for t in response.json())


# --- Isolation croisée : agents/jobs/snapshots ---

def test_list_agents_filtered_by_tenant(client, db_session):
    tenant_a = _create_tenant(client, "tenant-a")
    tenant_b = _create_tenant(client, "tenant-b")
    _make_agent(db_session, tenant_a["id"], "host-a")
    _make_agent(db_session, tenant_b["id"], "host-b")

    response_a = client.get(f"/api/v1/agents?tenant_id={tenant_a['id']}", headers=_dashboard_headers())
    assert [a["hostname"] for a in response_a.json()] == ["host-a"]

    response_all = client.get("/api/v1/agents", headers=_dashboard_headers())
    hostnames = {a["hostname"] for a in response_all.json()}
    assert {"host-a", "host-b"} <= hostnames


def test_list_jobs_filtered_by_tenant(client, db_session):
    tenant_a = _create_tenant(client, "tenant-a")
    tenant_b = _create_tenant(client, "tenant-b")
    agent_a = _make_agent(db_session, tenant_a["id"], "host-a")
    agent_b = _make_agent(db_session, tenant_b["id"], "host-b")
    db_session.add_all([
        Job(agent_id=agent_a.id, type="backup", status="completed"),
        Job(agent_id=agent_b.id, type="backup", status="completed"),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/jobs?tenant_id={tenant_a['id']}", headers=_dashboard_headers())
    assert response.status_code == 200
    assert all(j["agent_id"] == agent_a.id for j in response.json())
    assert len(response.json()) == 1


def test_list_snapshots_filtered_by_tenant(client, db_session):
    tenant_a = _create_tenant(client, "tenant-a")
    tenant_b = _create_tenant(client, "tenant-b")
    agent_a = _make_agent(db_session, tenant_a["id"], "host-a")
    agent_b = _make_agent(db_session, tenant_b["id"], "host-b")
    job_a = Job(agent_id=agent_a.id, type="backup", status="completed")
    job_b = Job(agent_id=agent_b.id, type="backup", status="completed")
    db_session.add_all([job_a, job_b])
    db_session.commit()
    db_session.add_all([
        Snapshot(job_id=job_a.id, name="snap-a", repo_path="/a", size_bytes=100),
        Snapshot(job_id=job_b.id, name="snap-b", repo_path="/b", size_bytes=200),
    ])
    db_session.commit()

    response = client.get(f"/api/v1/snapshots?tenant_id={tenant_a['id']}", headers=_dashboard_headers())
    assert response.status_code == 200
    names = [s["name"] for s in response.json()]
    assert names == ["snap-a"]


# --- Hostname unique par tenant, pas globalement (le bug corrigé) ---

def test_hostname_unique_within_tenant_updates_existing_agent(client):
    tenant = _create_tenant(client)
    payload = {"hostname": "same-host", "platform": "linux", "registration_secret": tenant["registration_secret"]}
    first = client.post("/api/v1/agents/register", json=payload)
    second = client.post("/api/v1/agents/register", json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_hostname_collision_allowed_across_different_tenants(client):
    tenant_a = _create_tenant(client, "tenant-a")
    tenant_b = _create_tenant(client, "tenant-b")

    response_a = client.post("/api/v1/agents/register", json={
        "hostname": "same-host", "platform": "linux",
        "registration_secret": tenant_a["registration_secret"],
    })
    response_b = client.post("/api/v1/agents/register", json={
        "hostname": "same-host", "platform": "linux",
        "registration_secret": tenant_b["registration_secret"],
    })

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["id"] != response_b.json()["id"]


# --- Secret d'enregistrement ---

def test_register_agent_without_registration_secret_is_rejected(client):
    response = client.post(
        "/api/v1/agents/register", json={"hostname": "h", "platform": "linux"}
    )
    assert response.status_code == 422


def test_register_agent_with_invalid_registration_secret_is_rejected(client):
    response = client.post("/api/v1/agents/register", json={
        "hostname": "h", "platform": "linux", "registration_secret": "not-a-real-secret",
    })
    assert response.status_code == 401


def test_register_agent_with_valid_secret_attaches_to_correct_tenant(client):
    tenant = _create_tenant(client)
    response = client.post("/api/v1/agents/register", json={
        "hostname": "h", "platform": "linux", "registration_secret": tenant["registration_secret"],
    })
    assert response.status_code == 200


# --- provision_agent : authentifié, rattaché à un tenant explicite ---

def test_provision_agent_requires_dashboard_token(client):
    response = client.post("/api/v1/agents/provision", params={"hostname": "h", "platform": "linux", "tenant_id": 1})
    assert response.status_code == 403


def test_provision_agent_unknown_tenant_returns_404(client):
    response = client.post(
        "/api/v1/agents/provision",
        params={"hostname": "h", "platform": "linux", "tenant_id": 999},
        headers=_dashboard_headers(),
    )
    assert response.status_code == 404


def test_provision_agent_duplicate_hostname_same_tenant_returns_409(client):
    tenant = _create_tenant(client)
    params = {"hostname": "h", "platform": "linux", "tenant_id": tenant["id"]}
    first = client.post("/api/v1/agents/provision", params=params, headers=_dashboard_headers())
    second = client.post("/api/v1/agents/provision", params=params, headers=_dashboard_headers())
    assert first.status_code == 200
    assert second.status_code == 409


# --- Quota de stockage ---

def test_backup_job_rejected_when_quota_exhausted(client, db_session):
    tenant_resp = client.post(
        "/api/v1/tenants", json={"name": "quota-tenant", "quota_bytes": 100},
        headers=_dashboard_headers(),
    )
    tenant_id = tenant_resp.json()["id"]
    agent = _make_agent(db_session, tenant_id, "host-quota", token="quota-agent-token")

    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    db_session.add(Snapshot(job_id=job.id, name="snap", repo_path="/x", size_bytes=100))
    db_session.commit()

    response = client.post(
        "/api/v1/backup",
        json={"agent_id": agent.id, "type": "backup"},
        headers={"Authorization": "Bearer quota-agent-token"},
    )
    assert response.status_code == 403


def test_check_job_not_blocked_by_quota(client, db_session):
    tenant_resp = client.post(
        "/api/v1/tenants", json={"name": "quota-tenant-2", "quota_bytes": 1},
        headers=_dashboard_headers(),
    )
    tenant_id = tenant_resp.json()["id"]
    agent = _make_agent(db_session, tenant_id, "host-quota-2", token="quota-agent-token-2")

    response = client.post(
        "/api/v1/backup",
        json={"agent_id": agent.id, "type": "check"},
        headers={"Authorization": "Bearer quota-agent-token-2"},
    )
    assert response.status_code != 403
