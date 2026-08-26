"""
Tests pour api/main.py::generate_agent_package. Vérifie que le paquet
généré est une archive valide contenant les VRAIS fichiers du package
agent/ (plus l'ancienne copie dupliquée et obsolète — sans snapshots,
config-show, ni la restauration), pour chaque plateforme supportée par
GET /download/agent/{platform}.
"""
import io
import json
import tarfile
import zipfile

from api.main import generate_agent_package


def test_generate_agent_package_windows_is_a_valid_zip_with_real_agent_files():
    package = generate_agent_package('windows')

    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        names = set(zf.namelist())
        assert {
            'agent/__init__.py', 'agent/cli.py', 'agent/config.py',
            'agent/api_client.py', 'agent/service.py',
            'requirements.txt', 'install.bat', 'config.json', 'README.txt',
        } <= names

        config = json.loads(zf.read('config.json'))
        assert config['platform'] == 'windows'

        cli_code = zf.read('agent/cli.py').decode()
        # Marqueurs du vrai CLI, absents de l'ancienne copie dupliquée :
        # restauration et gestion de service, ajoutées après coup à l'agent.
        assert '@click.group()' in cli_code
        assert 'def apply_restores' in cli_code
        assert "def service_install" in cli_code

        requirements = zf.read('requirements.txt').decode()
        assert 'click' in requirements
        assert 'borgbackup' not in requirements  # jamais importé par agent/


def test_generate_agent_package_linux_is_a_valid_tar_gz_with_real_agent_files():
    package = generate_agent_package('linux')

    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as tf:
        names = set(tf.getnames())
        assert {
            'agent/__init__.py', 'agent/cli.py', 'agent/config.py',
            'agent/api_client.py', 'agent/service.py',
            'requirements.txt', 'install.sh', 'config.json', 'README.md',
        } <= names

        config = json.loads(tf.extractfile('config.json').read())
        assert config['platform'] == 'linux'

        cli_code = tf.extractfile('agent/cli.py').read().decode()
        assert 'def apply_restores' in cli_code

        install_sh_info = tf.getmember('install.sh')
        assert install_sh_info.mode & 0o111  # exécutable


def test_generate_agent_package_macos_is_a_valid_tar_gz():
    package = generate_agent_package('macos')

    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as tf:
        config = json.loads(tf.extractfile('config.json').read())
        assert config['platform'] == 'macos'


def test_generate_agent_package_verify_ssl_false_for_default_localhost_host(monkeypatch):
    monkeypatch.delenv('API_HOST', raising=False)
    package = generate_agent_package('linux')

    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as tf:
        config = json.loads(tf.extractfile('config.json').read())
        assert config['verify_ssl'] is False


def test_generate_agent_package_verify_ssl_true_for_public_api_host(monkeypatch):
    monkeypatch.setenv('API_HOST', 'api.saveos.com')
    package = generate_agent_package('windows')

    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        config = json.loads(zf.read('config.json'))
        assert config['verify_ssl'] is True
