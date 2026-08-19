"""
Tests de non-régression :
- Job.config doit être stocké en JSON valide (round-trip via json.loads),
  et non via str() (repr Python invalide en JSON).
- Les relations Job<->Snapshot (deux FK croisées) ne doivent pas provoquer
  d'AmbiguousForeignKeysError lors des requêtes jointes.
"""
import json
from unittest.mock import patch

from api.database import Job


def test_create_backup_job_config_round_trips_as_json(client, db_session, test_agent):
    """Le config JSON envoyé à la création d'un job doit être relisible tel quel."""
    agent, token = test_agent

    with patch("api.main.enqueue_backup_job", return_value="fake-rq-job-id"):
        response = client.post(
            "/api/v1/backup",
            json={
                "agent_id": agent.id,
                "type": "backup",
                "config": {"source_paths": ["/data/docs"], "repo_path": "/tmp/repo"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    job_id = response.json()["id"]

    job = db_session.query(Job).filter(Job.id == job_id).first()
    # Avant le fix, job.config valait str({...}) : json.loads() levait une exception.
    parsed_config = json.loads(job.config)
    assert parsed_config == {"source_paths": ["/data/docs"], "repo_path": "/tmp/repo"}


def test_list_agent_snapshots_does_not_raise_ambiguous_fk(client, test_agent):
    """La jointure Snapshot<->Job doit être explicite, sans AmbiguousForeignKeysError."""
    agent, token = test_agent

    response = client.get(
        f"/api/v1/backup/{agent.id}/snapshots",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_agent_stats_does_not_raise_ambiguous_fk(client, test_agent):
    """Même jointure Snapshot<->Job que ci-dessus, exercée via /agents/stats."""
    agent, token = test_agent

    response = client.get(
        "/api/v1/agents/stats",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
