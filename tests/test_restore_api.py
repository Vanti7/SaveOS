"""
Tests pour les endpoints de restauration granulaire
(api/routers/restore.py) et les 3 endpoints liste-tout du tableau de bord.
"""
import json
import os
from unittest.mock import patch

import pytest

from api.database import Job, Snapshot

DASHBOARD_TOKEN = "test-dashboard-token"


@pytest.fixture(autouse=True)
def dashboard_token_env(monkeypatch):
    monkeypatch.setenv("DASHBOARD_API_TOKEN", DASHBOARD_TOKEN)


def _make_snapshot(db_session, agent, name="archive1"):
    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    snapshot = Snapshot(job_id=job.id, name=name, repo_path="/tmp/repo", size_bytes=10, is_full=True)
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


# --- Endpoints liste-tout (dashboard uniquement) ---

@pytest.mark.parametrize("path", ["/api/v1/agents", "/api/v1/jobs", "/api/v1/snapshots"])
def test_list_all_endpoints_reject_agent_token(client, test_agent, path):
    _, token = test_agent
    response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/agents", "/api/v1/jobs", "/api/v1/snapshots"])
def test_list_all_endpoints_accept_dashboard_token(client, path):
    response = client.get(path, headers={"Authorization": f"Bearer {DASHBOARD_TOKEN}"})
    assert response.status_code == 200


# --- browse ---

@patch("api.routers.restore.BorgManager.list_archive_contents")
def test_browse_snapshot_contents_buckets_one_level(mock_list, client, db_session, test_agent):
    agent, token = test_agent
    snapshot = _make_snapshot(db_session, agent)

    mock_list.return_value = {
        'success': True,
        'entries': [
            {'path': 'docs', 'type': 'd', 'size': 0, 'mtime': None},
            {'path': 'docs/a.txt', 'type': 'f', 'size': 10, 'mtime': None},
            {'path': 'docs/sub/b.txt', 'type': 'f', 'size': 20, 'mtime': None},
            {'path': 'readme.txt', 'type': 'f', 'size': 5, 'mtime': None},
        ],
        'stderr': '',
    }

    response = client.post(
        f"/api/v1/backup/{agent.id}/snapshots/{snapshot.id}/browse",
        json={"path": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    paths = {e['path'] for e in response.json()['entries']}
    assert paths == {'docs', 'readme.txt'}


def test_browse_snapshot_rejects_other_agent(client, db_session, test_agent):
    agent, token = test_agent
    from api.database import Agent as AgentModel
    from api.auth import AuthManager

    other = AgentModel(tenant_id=agent.tenant_id, hostname="other", platform="linux",
                        token=AuthManager.hash_token("other-token"), status="active")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)
    snapshot = _make_snapshot(db_session, other)

    response = client.post(
        f"/api/v1/backup/{other.id}/snapshots/{snapshot.id}/browse",
        json={"path": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


# --- create_restore_job ---

@patch("api.routers.restore.enqueue_restore_job", return_value="rq-1")
def test_create_restore_job_download_target(mock_enqueue, client, db_session, test_agent):
    agent, token = test_agent
    snapshot = _make_snapshot(db_session, agent)

    response = client.post(
        "/api/v1/restore",
        json={
            "agent_id": agent.id, "snapshot_id": snapshot.id,
            "selected_paths": ["docs/a.txt"], "target": "download",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    job_id = response.json()["id"]
    job = db_session.query(Job).filter(Job.id == job_id).first()
    assert job.type == "restore"
    assert json.loads(job.config)["selected_paths"] == ["docs/a.txt"]
    mock_enqueue.assert_called_once_with(job_id)


def test_create_restore_job_requires_restore_path_for_agent_target(client, db_session, test_agent):
    agent, token = test_agent
    snapshot = _make_snapshot(db_session, agent)

    response = client.post(
        "/api/v1/restore",
        json={
            "agent_id": agent.id, "snapshot_id": snapshot.id,
            "selected_paths": ["docs/a.txt"], "target": "agent",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_create_restore_job_rejects_empty_selection(client, db_session, test_agent):
    agent, token = test_agent
    snapshot = _make_snapshot(db_session, agent)

    response = client.post(
        "/api/v1/restore",
        json={"agent_id": agent.id, "snapshot_id": snapshot.id, "selected_paths": [], "target": "download"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@patch("api.routers.restore.enqueue_restore_job", return_value="rq-2")
def test_create_restore_job_dashboard_can_act_for_any_agent(mock_enqueue, client, db_session, test_agent):
    agent, _ = test_agent
    snapshot = _make_snapshot(db_session, agent)

    response = client.post(
        "/api/v1/restore",
        json={
            "agent_id": agent.id, "snapshot_id": snapshot.id,
            "selected_paths": ["docs/a.txt"], "target": "download",
        },
        headers={"Authorization": f"Bearer {DASHBOARD_TOKEN}"},
    )
    assert response.status_code == 200


# --- download_restore_package ---

def test_download_restore_package_not_ready_returns_409(client, db_session, test_agent):
    agent, token = test_agent
    job = Job(agent_id=agent.id, type="restore", status="running", config=json.dumps({}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/v1/restore/{job.id}/download", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 409


def test_download_restore_package_streams_existing_zip(client, db_session, test_agent, tmp_path):
    agent, token = test_agent
    package = tmp_path / "1.zip"
    package.write_bytes(b"PK\x03\x04fake-zip-content")

    job = Job(
        agent_id=agent.id, type="restore", status="completed",
        config=json.dumps({"package_path": str(package)}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/v1/restore/{job.id}/download", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.content == b"PK\x03\x04fake-zip-content"


def test_download_restore_package_rejects_other_agent(client, db_session, test_agent):
    agent, token = test_agent
    from api.database import Agent as AgentModel
    from api.auth import AuthManager

    other = AgentModel(tenant_id=agent.tenant_id, hostname="other2", platform="linux",
                        token=AuthManager.hash_token("other-token-2"), status="active")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    job = Job(agent_id=other.id, type="restore", status="completed", config=json.dumps({"package_path": "/tmp/x.zip"}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/v1/restore/{job.id}/download", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_download_restore_package_missing_job_returns_404(client, test_agent):
    _, token = test_agent
    response = client.get("/api/v1/restore/9999/download", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


# --- list_pending_restores / report_restore_status ---

def test_list_pending_restores_only_returns_ready_for_agent(client, db_session, test_agent):
    agent, token = test_agent
    ready = Job(agent_id=agent.id, type="restore", status="ready_for_agent", config=json.dumps({"restore_path": "/x"}))
    running = Job(agent_id=agent.id, type="restore", status="running", config=json.dumps({}))
    db_session.add_all([ready, running])
    db_session.commit()

    response = client.get("/api/v1/agents/me/pending-restores", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["config"]["restore_path"] == "/x"


def test_report_restore_status_completed(client, db_session, test_agent):
    agent, token = test_agent
    job = Job(agent_id=agent.id, type="restore", status="ready_for_agent", config=json.dumps({}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.post(
        f"/api/v1/jobs/{job.id}/agent-report",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_report_restore_status_rejects_wrong_state(client, db_session, test_agent):
    agent, token = test_agent
    job = Job(agent_id=agent.id, type="restore", status="pending", config=json.dumps({}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.post(
        f"/api/v1/jobs/{job.id}/agent-report",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


def test_report_restore_status_rejects_other_agent(client, db_session, test_agent):
    agent, token = test_agent
    from api.database import Agent as AgentModel
    from api.auth import AuthManager

    other = AgentModel(tenant_id=agent.tenant_id, hostname="other3", platform="linux",
                        token=AuthManager.hash_token("other-token-3"), status="active")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    job = Job(agent_id=other.id, type="restore", status="ready_for_agent", config=json.dumps({}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.post(
        f"/api/v1/jobs/{job.id}/agent-report",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
