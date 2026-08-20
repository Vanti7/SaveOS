"""
Tests pour l'API SaveOS
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    """Test du endpoint de santé"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_metrics(client):
    """Test du endpoint de métriques (format d'exposition Prometheus, cf.
    tests/test_metrics_api.py pour la couverture détaillée)"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

@pytest.mark.integration
def test_register_agent():
    """Test d'enregistrement d'un agent"""
    agent_data = {
        "hostname": "test-host",
        "platform": "linux",
        "config": {"test": "value"}
    }
    response = client.post("/api/v1/agents/register", json=agent_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["hostname"] == "test-host"
    assert data["platform"] == "linux"
    assert "token" in data