"""
Tests pour api/main.py::generate_agent_package : jusqu'ici sans aucune
couverture. Vérifie que le paquet généré est une archive valide contenant
les fichiers attendus, pour chaque plateforme supportée par le endpoint
GET /download/agent/{platform}.
"""
import io
import json
import tarfile
import zipfile

from api.main import generate_agent_package


def test_generate_agent_package_windows_is_a_valid_zip_with_expected_files():
    package = generate_agent_package('windows')

    with zipfile.ZipFile(io.BytesIO(package)) as zf:
        names = set(zf.namelist())
        assert {'agent.py', 'requirements.txt', 'install.bat', 'config.json', 'README.txt'} <= names

        config = json.loads(zf.read('config.json'))
        assert config['platform'] == 'windows'

        agent_code = zf.read('agent.py').decode()
        assert 'class SaveOSAgent' in agent_code


def test_generate_agent_package_linux_is_a_valid_tar_gz_with_expected_files():
    package = generate_agent_package('linux')

    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as tf:
        names = set(tf.getnames())
        assert {'agent.py', 'requirements.txt', 'install.sh', 'config.json', 'README.md'} <= names

        config = json.loads(tf.extractfile('config.json').read())
        assert config['platform'] == 'linux'

        install_sh_info = tf.getmember('install.sh')
        assert install_sh_info.mode & 0o111  # exécutable


def test_generate_agent_package_macos_is_a_valid_tar_gz():
    package = generate_agent_package('macos')

    with tarfile.open(fileobj=io.BytesIO(package), mode='r:gz') as tf:
        config = json.loads(tf.extractfile('config.json').read())
        assert config['platform'] == 'macos'
