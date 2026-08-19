"""
Tests pour l'authentification double agent/tableau de bord
(api/auth.py: Principal, get_current_principal, require_dashboard).
"""
import pytest

DASHBOARD_TOKEN = "test-dashboard-token"


@pytest.fixture(autouse=True)
def dashboard_token_env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_TOKEN", DASHBOARD_TOKEN)


def test_list_snapshots_agent_can_access_own(client, test_agent):
    agent, token = test_agent

    response = client.get(
        f"/api/v1/backup/{agent.id}/snapshots",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_list_snapshots_agent_cannot_access_other(client, test_agent, db_session):
    from api.database import Agent
    from api.auth import AuthManager

    agent, token = test_agent
    other = Agent(
        tenant_id=agent.tenant_id,
        hostname="other-host",
        platform="linux",
        token=AuthManager.hash_token("other-token"),
        status="active",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    response = client.get(
        f"/api/v1/backup/{other.id}/snapshots",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_list_snapshots_dashboard_can_access_any_agent(client, test_agent):
    agent, _ = test_agent

    response = client.get(
        f"/api/v1/backup/{agent.id}/snapshots",
        headers={"Authorization": f"Bearer {DASHBOARD_TOKEN}"},
    )

    assert response.status_code == 200


def test_invalid_token_is_rejected(client, test_agent):
    agent, _ = test_agent

    response = client.get(
        f"/api/v1/backup/{agent.id}/snapshots",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_get_job_status_dashboard_can_access_any_agents_job(client, test_agent, db_session):
    from api.database import Job

    agent, _ = test_agent
    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers={"Authorization": f"Bearer {DASHBOARD_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == job.id


def test_get_job_status_agent_cannot_access_others_job(client, test_agent, db_session):
    from api.database import Agent, Job
    from api.auth import AuthManager

    agent, token = test_agent
    other = Agent(
        tenant_id=agent.tenant_id,
        hostname="other-host",
        platform="linux",
        token=AuthManager.hash_token("other-token"),
        status="active",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    job = Job(agent_id=other.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(
        f"/api/v1/jobs/{job.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
