"""
Tests pour GET /download/agent/{platform}/installer : redirection vers
l'asset GitHub Release correspondant à la VERSION courante, uniquement s'il
existe réellement (voir docs/adr/0008-installateur-erreur-claire.md — sans
cette vérification, GitHub renvoyait un 404 opaque quand aucune release
n'avait été publiée). Aucun appel réseau réel — VERSION, GITHUB_REPO et
l'existence de l'asset sont contrôlés pour un test déterministe.
"""
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from api.main import _release_asset_exists


@pytest.fixture(autouse=True)
def asset_exists_by_default():
    """Par défaut, l'asset "existe" pour ne pas casser les tests de
    redirection existants — les tests du cas 404 le patchent explicitement."""
    with patch('api.main._release_asset_exists', return_value=True):
        yield


def test_installer_redirect_windows(client):
    with patch('api.main._get_current_version', return_value='1.5.0'):
        response = client.get('/download/agent/windows/installer', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['location'] == (
        'https://github.com/Vanti7/SaveOS/releases/download/v1.5.0/'
        'SaveOS-Agent-Setup-1.5.0-windows.exe'
    )


def test_installer_redirect_macos(client):
    with patch('api.main._get_current_version', return_value='1.5.0'):
        response = client.get('/download/agent/macos/installer', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['location'] == (
        'https://github.com/Vanti7/SaveOS/releases/download/v1.5.0/'
        'SaveOS-Agent-1.5.0-macos.dmg'
    )


def test_installer_redirect_linux(client):
    with patch('api.main._get_current_version', return_value='1.5.0'):
        response = client.get('/download/agent/linux/installer', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['location'] == (
        'https://github.com/Vanti7/SaveOS/releases/download/v1.5.0/'
        'saveos-agent_1.5.0_amd64.deb'
    )


def test_installer_redirect_uses_github_repo_env_var(client, monkeypatch):
    monkeypatch.setenv('GITHUB_REPO', 'someone-else/fork')
    with patch('api.main._get_current_version', return_value='2.0.0'):
        response = client.get('/download/agent/linux/installer', follow_redirects=False)

    assert 'someone-else/fork' in response.headers['location']


def test_installer_redirect_rejects_unknown_platform(client):
    response = client.get('/download/agent/bsd/installer', follow_redirects=False)
    assert response.status_code == 400


def test_installer_returns_clear_404_when_no_release_published(client):
    with patch('api.main._get_current_version', return_value='1.5.0'), \
         patch('api.main._release_asset_exists', return_value=False):
        response = client.get('/download/agent/windows/installer', follow_redirects=False)

    assert response.status_code == 404
    assert 'Aucun installeur natif publié' in response.json()['detail']


# --- _release_asset_exists : logique de vérification elle-même ---

@patch('api.main.urllib.request.urlopen')
def test_release_asset_exists_true_on_200(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value = MagicMock(status=200)
    assert _release_asset_exists('https://github.com/x/y/releases/download/v1/a.exe') is True


@patch('api.main.urllib.request.urlopen', side_effect=urllib.error.HTTPError(
    'https://x', 404, 'Not Found', None, None
))
def test_release_asset_exists_false_on_404(mock_urlopen):
    assert _release_asset_exists('https://github.com/x/y/releases/download/v1/a.exe') is False


@patch('api.main.urllib.request.urlopen', side_effect=urllib.error.URLError('network unreachable'))
def test_release_asset_exists_true_when_network_unavailable(mock_urlopen):
    # Ne bloque pas l'utilisateur pour une raison indépendante de
    # l'existence réelle de la release.
    assert _release_asset_exists('https://github.com/x/y/releases/download/v1/a.exe') is True
