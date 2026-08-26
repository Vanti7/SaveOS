"""
Tests pour agent/config.py (AgentConfig) : jusqu'ici sans aucune couverture.
"""
from unittest.mock import patch

from agent.config import AgentConfig


def test_init_creates_config_dir(tmp_path):
    config_dir = tmp_path / "saveos"
    AgentConfig(config_dir=str(config_dir))
    assert config_dir.is_dir()


def test_load_config_creates_file_with_defaults_on_first_run(tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    config = config_manager.load_config()

    assert config['api_url'] == 'https://localhost:8000'
    assert config['heartbeat_interval'] == 300
    assert config['verify_ssl'] is False  # hôte par défaut = localhost (self-signed)
    assert (tmp_path / 'config.json').exists()


def test_save_then_load_config_round_trips_and_merges_with_defaults(tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    config_manager.save_config({'api_url': 'https://custom.example:9000'})

    reloaded = config_manager.load_config()

    assert reloaded['api_url'] == 'https://custom.example:9000'
    # Les clés absentes du fichier sauvegardé restent comblées par les défauts
    assert reloaded['heartbeat_interval'] == 300


def test_load_config_falls_back_to_defaults_on_corrupt_file(tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    (tmp_path / 'config.json').write_text('{not valid json', encoding='utf-8')

    config = config_manager.load_config()

    assert config == config_manager.default_config


def test_token_save_get_delete_round_trip(tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))

    assert config_manager.get_token() is None

    assert config_manager.save_token('secret-token-123') is True
    assert config_manager.get_token() == 'secret-token-123'

    assert config_manager.delete_token() is True
    assert config_manager.get_token() is None


def test_delete_token_when_absent_is_a_noop_success(tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    assert config_manager.delete_token() is True


@patch('agent.config.platform.system', return_value='Windows')
def test_default_source_paths_windows(mock_system, tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    paths = config_manager._get_default_source_paths()
    assert any('Documents' in p for p in paths)
    assert not any('Videos' in p or 'Movies' in p for p in paths)


@patch('agent.config.platform.system', return_value='Darwin')
def test_default_source_paths_macos(mock_system, tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    paths = config_manager._get_default_source_paths()
    assert any('Movies' in p for p in paths)


@patch('agent.config.platform.system', return_value='Linux')
def test_default_source_paths_linux(mock_system, tmp_path):
    config_manager = AgentConfig(config_dir=str(tmp_path))
    paths = config_manager._get_default_source_paths()
    assert any('Videos' in p for p in paths)


# --- _default_verify_ssl : dérivation selon l'hôte (docs/adr/0003) ---

def test_default_verify_ssl_is_false_for_localhost():
    assert AgentConfig._default_verify_ssl('https://localhost:8000') is False


def test_default_verify_ssl_is_false_for_loopback_ip():
    assert AgentConfig._default_verify_ssl('https://127.0.0.1:8000') is False


def test_default_verify_ssl_is_true_for_real_host():
    assert AgentConfig._default_verify_ssl('https://api.saveos.com') is True
