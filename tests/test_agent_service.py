"""
Tests pour agent/service.py (ServiceManager) : jusqu'ici sans aucune
couverture. subprocess.run et l'écriture de fichiers système sont mockés —
ces tests ne doivent jamais toucher le vrai systemd/launchd/schtasks de la
machine qui les exécute.
"""
from unittest.mock import MagicMock, mock_open, patch

from agent.service import ServiceManager


def _manager(platform_name):
    with patch('agent.service.platform.system', return_value=platform_name):
        return ServiceManager('/opt/saveos/agent.py')


# --- install_service : dispatch par plateforme ---

def test_install_service_unsupported_platform():
    manager = _manager('SunOS')
    result = manager.install_service()
    assert result['success'] is False
    assert 'non supportée' in result['error']


@patch('agent.service.subprocess.run')
def test_install_service_linux_calls_systemctl(mock_run):
    manager = _manager('Linux')
    mock_run.return_value = MagicMock(returncode=0)

    with patch('builtins.open', mock_open()):
        result = manager.install_service()

    assert result['success'] is True
    called_commands = [call.args[0] for call in mock_run.call_args_list]
    assert ['sudo', 'systemctl', 'daemon-reload'] in called_commands
    assert ['sudo', 'systemctl', 'enable', 'saveos-agent'] in called_commands


@patch('agent.service.subprocess.run')
def test_install_service_linux_reports_systemctl_failure(mock_run):
    import subprocess as subprocess_module
    manager = _manager('Linux')
    mock_run.side_effect = subprocess_module.CalledProcessError(1, ['systemctl'])

    with patch('builtins.open', mock_open()):
        result = manager.install_service()

    assert result['success'] is False
    assert 'systemctl' in result['error']


@patch('agent.service.subprocess.run')
def test_install_service_macos_calls_launchctl(mock_run):
    manager = _manager('Darwin')
    mock_run.return_value = MagicMock(returncode=0)

    with patch('builtins.open', mock_open()):
        result = manager.install_service()

    assert result['success'] is True
    mock_run.assert_called_once_with(
        ['sudo', 'launchctl', 'load', '/Library/LaunchDaemons/com.saveos.agent.plist'],
        check=True,
    )


def test_install_service_windows_without_pywin32_reports_clear_error():
    # install_service() importe win32serviceutil/win32service/win32event/
    # servicemanager avant de déléguer à la tâche planifiée : sur une machine
    # sans pywin32 (comme cet environnement de test), c'est le comportement
    # réel constaté pour un utilisateur.
    manager = _manager('Windows')
    result = manager.install_service()
    assert result['success'] is False
    assert 'pywin32' in result['error']


@patch('agent.service.subprocess.run')
def test_install_windows_task_creates_scheduled_task(mock_run):
    manager = _manager('Windows')
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

    result = manager._install_windows_task()

    assert result['success'] is True
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[:3] == ['schtasks', '/create', '/tn']
    assert 'SaveOS Agent' in cmd


@patch('agent.service.subprocess.run')
def test_install_windows_task_reports_schtasks_failure(mock_run):
    manager = _manager('Windows')
    mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='accès refusé')

    result = manager._install_windows_task()

    assert result['success'] is False
    assert 'accès refusé' in result['error']


# --- start_service / stop_service / get_service_status ---

@patch('agent.service.subprocess.run')
def test_start_service_linux(mock_run):
    manager = _manager('Linux')
    mock_run.return_value = MagicMock(returncode=0)

    result = manager.start_service()

    assert result['success'] is True
    mock_run.assert_called_once_with(['sudo', 'systemctl', 'start', 'saveos-agent'], check=True)


@patch('agent.service.subprocess.run')
def test_stop_service_reports_failure(mock_run):
    import subprocess as subprocess_module
    manager = _manager('Linux')
    mock_run.side_effect = subprocess_module.CalledProcessError(1, ['systemctl'])

    result = manager.stop_service()

    assert result['success'] is False


@patch('agent.service.subprocess.run')
def test_get_service_status_linux_active(mock_run):
    manager = _manager('Linux')
    mock_run.return_value = MagicMock(returncode=0, stdout='active\n', stderr='')

    result = manager.get_service_status()

    assert result['success'] is True
    assert result['active'] is True
    assert result['status'] == 'running'


@patch('agent.service.subprocess.run')
def test_get_service_status_linux_inactive(mock_run):
    manager = _manager('Linux')
    mock_run.return_value = MagicMock(returncode=0, stdout='inactive\n', stderr='')

    result = manager.get_service_status()

    assert result['active'] is False
    assert result['status'] == 'stopped'
