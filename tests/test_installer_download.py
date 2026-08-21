"""
Tests pour GET /download/agent/{platform}/installer : redirection vers
l'asset GitHub Release correspondant à la VERSION courante. Aucun appel
réseau réel — VERSION et GITHUB_REPO sont contrôlés pour un test
déterministe.
"""
from unittest.mock import patch


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
