"""
Tests pour la commande `agent.cli register` : dérivation de verify_ssl
selon l'hôte de --api-url (voir docs/adr/0003-certificats-tls-production.md),
et override explicite via --verify-ssl/--no-verify-ssl. SaveOSAPIClient est
mocké — ces tests ne doivent jamais faire d'appel réseau réel.
"""
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agent.cli import cli
from agent.config import AgentConfig


def _register(tmp_path, args):
    mock_client = MagicMock()
    mock_client.register_agent.return_value = {
        'success': True,
        'data': {'id': 1, 'hostname': 'h', 'platform': 'linux', 'status': 'active', 'token': 'tok'},
    }
    with patch('agent.cli.SaveOSAPIClient', return_value=mock_client):
        runner = CliRunner()
        result = runner.invoke(cli, ['--config-dir', str(tmp_path), 'register', *args])
    assert result.exit_code == 0, result.output
    return AgentConfig(config_dir=str(tmp_path)).load_config()


def test_register_with_public_api_url_enables_verify_ssl(tmp_path):
    config = _register(tmp_path, ['--api-url', 'https://api.saveos.com'])
    assert config['verify_ssl'] is True


def test_register_with_localhost_api_url_disables_verify_ssl(tmp_path):
    config = _register(tmp_path, ['--api-url', 'https://localhost:9000'])
    assert config['verify_ssl'] is False


def test_register_explicit_no_verify_ssl_overrides_public_host(tmp_path):
    config = _register(tmp_path, ['--api-url', 'https://api.saveos.com', '--no-verify-ssl'])
    assert config['verify_ssl'] is False


def test_register_explicit_verify_ssl_overrides_localhost(tmp_path):
    config = _register(tmp_path, ['--api-url', 'https://localhost:9000', '--verify-ssl'])
    assert config['verify_ssl'] is True
