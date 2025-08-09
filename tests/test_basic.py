#!/usr/bin/env python3
"""
Tests basiques pour SaveOS - Workflow Development
Tests légers qui s'exécutent rapidement sans services externes
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch

# Ajouter les modules SaveOS au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test que les modules principaux peuvent être importés"""
    try:
        from api import database, schemas, auth
        from agent import config, api_client
        from worker import tasks
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_database_models():
    """Test basique des modèles de base de données"""
    from api.database import Tenant, User, Agent, Job, Snapshot
    
    # Test que les classes existent et ont les attributs attendus
    assert hasattr(Tenant, 'id')
    assert hasattr(Tenant, 'name')
    assert hasattr(User, 'id')
    assert hasattr(User, 'username')
    assert hasattr(Agent, 'id')
    assert hasattr(Agent, 'hostname')
    assert hasattr(Job, 'id')
    assert hasattr(Job, 'type')
    assert hasattr(Snapshot, 'id')
    assert hasattr(Snapshot, 'path')

def test_schemas():
    """Test basique des schémas Pydantic"""
    from api.schemas import AgentRegister, JobCreate, SnapshotResponse
    
    # Test création d'un schéma agent
    agent_data = {
        "hostname": "test-host",
        "platform": "linux"
    }
    agent_schema = AgentRegister(**agent_data)
    assert agent_schema.hostname == "test-host"
    assert agent_schema.platform == "linux"

def test_auth_functions():
    """Test basique des fonctions d'authentification"""
    from api.auth import AuthManager
    
    # Test génération de token
    token = AuthManager.generate_agent_token()
    assert isinstance(token, str)
    assert len(token) > 10
    
    # Test hash de token
    hashed = AuthManager.hash_token(token)
    assert isinstance(hashed, str)
    assert hashed != token

def test_agent_config():
    """Test basique de la configuration d'agent"""
    from agent.config import AgentConfig
    
    # Test configuration par défaut
    config = AgentConfig()
    assert hasattr(config, 'api_url')
    assert hasattr(config, 'token')
    assert hasattr(config, 'hostname')

@patch('requests.post')
def test_agent_api_client(mock_post):
    """Test basique du client API d'agent"""
    from agent.api_client import SaveOSClient
    
    # Mock de la réponse
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_post.return_value = mock_response
    
    # Test du client
    client = SaveOSClient("https://test.api", "test-token")
    result = client.register("test-host", "linux")
    
    assert result is not None
    mock_post.assert_called_once()

def test_version_file():
    """Test que le fichier VERSION existe et est valide"""
    version_file = os.path.join(os.path.dirname(__file__), '..', 'VERSION')
    assert os.path.exists(version_file)
    
    with open(version_file, 'r') as f:
        version = f.read().strip()
    
    # Test format version sémantique basique
    parts = version.split('.')
    assert len(parts) >= 2
    assert all(part.isdigit() for part in parts[:2])

def test_requirements():
    """Test que le fichier requirements.txt existe"""
    req_file = os.path.join(os.path.dirname(__file__), '..', 'requirements.txt')
    assert os.path.exists(req_file)
    
    with open(req_file, 'r') as f:
        content = f.read()
    
    # Vérifier quelques dépendances critiques
    assert 'fastapi' in content
    assert 'sqlalchemy' in content
    assert 'redis' in content

def test_docker_files():
    """Test que les Dockerfiles existent"""
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    
    dockerfiles = [
        'Dockerfile.api',
        'Dockerfile.worker', 
        'Dockerfile.prod',
        'docker-compose.yml',
        'docker-compose.prod.yml'
    ]
    
    for dockerfile in dockerfiles:
        filepath = os.path.join(base_dir, dockerfile)
        assert os.path.exists(filepath), f"Missing {dockerfile}"

def test_scripts():
    """Test que les scripts principaux existent"""
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    
    scripts = [
        'version.py',
        'smoke_tests.py',
        'setup.sh',
        'setup.ps1'
    ]
    
    for script in scripts:
        filepath = os.path.join(scripts_dir, script)
        assert os.path.exists(filepath), f"Missing script {script}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])