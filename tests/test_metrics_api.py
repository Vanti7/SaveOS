"""
Tests pour l'endpoint /metrics (format d'exposition Prometheus réel,
jauges recalculées depuis la DB à chaque scrape).
"""
import json

from api.database import Agent, Job, Snapshot
from api.auth import AuthManager


def _make_agent(db_session, tenant_id, hostname, status="active"):
    agent = Agent(
        tenant_id=tenant_id, hostname=hostname, platform="linux",
        token=AuthManager.hash_token(f"token-{hostname}"), status=status,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def test_metrics_returns_prometheus_text_format(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    # Ancien stub JSON : plus de clés agents_total/jobs_total en JSON
    assert not response.text.startswith("{")


def test_metrics_reflects_db_state(client, db_session, test_agent):
    agent, _ = test_agent
    other = _make_agent(db_session, agent.tenant_id, "other-host", status="error")

    job = Job(agent_id=agent.id, type="backup", status="completed")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    snapshot = Snapshot(job_id=job.id, name="archive1", repo_path="/tmp/repo", size_bytes=1000, is_full=True)
    db_session.add(snapshot)
    db_session.commit()

    body = client.get("/metrics").text

    assert 'saveos_agents_total{status="active"} 1.0' in body
    assert 'saveos_agents_total{status="error"} 1.0' in body
    assert 'saveos_jobs_total{status="completed",type="backup"} 1.0' in body
    assert "saveos_snapshots_total 1.0" in body
    assert "saveos_snapshots_size_bytes_total 1000.0" in body


def test_metrics_gauges_do_not_leak_stale_label_combinations(client, db_session, test_agent):
    agent, _ = test_agent

    job = Job(agent_id=agent.id, type="backup", status="pending")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    first_body = client.get("/metrics").text
    assert 'saveos_jobs_total{status="pending",type="backup"} 1.0' in first_body

    # Le job change de statut : l'ancienne combinaison de labels ne doit
    # plus apparaître après un nouveau scrape (Gauge.clear() avant repeuplement).
    job.status = "completed"
    db_session.commit()

    second_body = client.get("/metrics").text
    assert 'saveos_jobs_total{status="pending",type="backup"}' not in second_body
    assert 'saveos_jobs_total{status="completed",type="backup"} 1.0' in second_body
