"""
Tests pour agent/service.py (ServiceManager) : jusqu'ici sans aucune
couverture. subprocess.run et l'écriture de fichiers système sont mockés —
ces tests ne doivent jamais toucher le vrai systemd/launchd/schtasks de la
machine qui les exécute.
"""
from unittest.mock import MagicMock, mock_open, patch

from agent.service import ServiceManager


def _manager(platform_name, agent_path='/opt/saveos/agent.py', is_frozen=False):
    with patch('agent.service.platform.system', return_value=platform_name):
        return ServiceManager(agent_path, is_frozen=is_frozen)


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


@patch('agent.service.subprocess.run')
def test_install_service_windows_delegates_to_scheduled_task(mock_run):
    # install_service() importait autrefois win32serviceutil/win32service/
    # win32event/servicemanager avant de déléguer à la tâche planifiée —
    # code mort jamais utilisé (l'implémentation réelle est schtasks, pas
    # pywin32) qui bloquait tout sur une machine utilisateur type (jamais
    # pywin32 installé). Découvert en testant un exécutable PyInstaller réel
    # (dist/saveos-agent.exe service install échouait systématiquement sur
    # "Module pywin32 requis"). Retiré : install_service() délègue
    # directement à _install_windows_task(), sans condition.
    manager = _manager('Windows')
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

    result = manager.install_service()

    assert result['success'] is True
    args, _ = mock_run.call_args
    assert args[0][:3] == ['schtasks', '/create', '/tn']


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


# --- Adaptation figé (PyInstaller) vs script Python ---
#
# Un exécutable figé EST l'interpréteur + le script : on l'invoque
# directement, sans le préfixer par `python3 <chemin>` comme pour un
# script .py lancé via un Python système installé sur la machine cible.

def test_exec_command_script_mode_prefixes_python3():
    manager = _manager('Linux', agent_path='/opt/agent.py', is_frozen=False)
    assert manager._exec_command('daemon') == '/usr/bin/python3 /opt/agent.py daemon'


def test_exec_command_frozen_mode_invokes_binary_directly():
    manager = _manager('Linux', agent_path='/opt/saveos-agent', is_frozen=True)
    assert manager._exec_command('daemon') == '/opt/saveos-agent daemon'


@patch('agent.service.subprocess.run')
def test_install_systemd_service_frozen_execstart_has_no_python_prefix(mock_run):
    manager = _manager('Linux', agent_path='/opt/saveos-agent', is_frozen=True)
    mock_run.return_value = MagicMock(returncode=0)

    m = mock_open()
    with patch('builtins.open', m):
        result = manager.install_service()

    written_content = ''.join(call.args[0] for call in m().write.call_args_list)
    assert result['success'] is True
    assert 'ExecStart=/opt/saveos-agent daemon' in written_content
    assert 'python3' not in written_content


@patch('agent.service.subprocess.run')
def test_install_launchd_service_frozen_program_arguments_has_no_python(mock_run):
    manager = _manager('Darwin', agent_path='/Applications/SaveOS Agent.app/Contents/MacOS/saveos-agent', is_frozen=True)
    mock_run.return_value = MagicMock(returncode=0)

    m = mock_open()
    with patch('builtins.open', m):
        result = manager.install_service()

    written_content = ''.join(call.args[0] for call in m().write.call_args_list)
    assert result['success'] is True
    assert '<string>/usr/bin/python3</string>' not in written_content
    assert 'saveos-agent</string>' in written_content


@patch('agent.service.subprocess.run')
def test_install_windows_task_frozen_uses_exe_as_command(mock_run):
    manager = _manager('Windows', agent_path=r'C:\Program Files\SaveOS Agent\saveos-agent.exe', is_frozen=True)

    captured_xml = {}

    def fake_run(cmd, **kwargs):
        # Le XML de la tâche est un vrai fichier temporaire (non mocké) au
        # moment de cet appel : on le lit avant qu'il ne soit supprimé.
        xml_path = cmd[cmd.index('/xml') + 1]
        # Le fichier a été écrit avec l'encodage par défaut de la plateforme
        # (tempfile.NamedTemporaryFile(mode='w'), pas forcément UTF-16 malgré
        # la déclaration XML) : on relit sans forcer d'encodage particulier.
        with open(xml_path) as f:
            captured_xml['content'] = f.read()
        return MagicMock(returncode=0, stdout='', stderr='')

    mock_run.side_effect = fake_run

    result = manager._install_windows_task()

    assert result['success'] is True
    assert '<Command>C:\\Program Files\\SaveOS Agent\\saveos-agent.exe</Command>' in captured_xml['content']
    assert '<Arguments>daemon</Arguments>' in captured_xml['content']


# --- Sous-groupe CLI `service` (agent/cli.py) ---

def test_cli_service_install_success(monkeypatch):
    from click.testing import CliRunner
    from agent.cli import cli

    mock_manager = MagicMock()
    mock_manager.install_service.return_value = {'success': True, 'message': 'Service installé'}
    with patch('agent.cli.ServiceManager', return_value=mock_manager):
        runner = CliRunner()
        result = runner.invoke(cli, ['service', 'install'])

    assert result.exit_code == 0
    assert 'installé' in result.output


def test_cli_service_status_reports_error(monkeypatch):
    from click.testing import CliRunner
    from agent.cli import cli

    mock_manager = MagicMock()
    mock_manager.get_service_status.return_value = {'success': False, 'error': 'boom'}
    with patch('agent.cli.ServiceManager', return_value=mock_manager):
        runner = CliRunner()
        result = runner.invoke(cli, ['service', 'status'])

    assert result.exit_code == 1
    assert 'boom' in result.output


def test_current_agent_path_uses_sys_executable_when_frozen(monkeypatch):
    from agent.cli import _current_agent_path
    import sys as sys_module

    monkeypatch.setattr(sys_module, 'frozen', True, raising=False)
    monkeypatch.setattr(sys_module, 'executable', '/opt/saveos-agent')

    assert _current_agent_path() == '/opt/saveos-agent'

    monkeypatch.delattr(sys_module, 'frozen', raising=False)
