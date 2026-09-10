"""
Tests structurels pour le build de l'image web : préviennent la régression
vers l'état « le stage builder n'installe que les `dependencies`, alors que
`next build` type-check aussi les fichiers qui importent les
`devDependencies` » — cause des 22 échecs consécutifs du déploiement staging
entre le 26/08 et le 11/09/2026 (voir
docs/adr/0011-build-web-devdependencies.md).

Assertions texte simples, sans dépendance à Docker — limite assumée : elles
ne vérifient que le drapeau d'installation, pas que le build passe réellement.
Le test @integration ci-dessous construit vraiment le stage ; la CI fait de
même sur chaque PR (job « Docker Check »).
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PROD = REPO_ROOT / 'Dockerfile.prod'
WEB_DOCKERFILE = REPO_ROOT / 'web' / 'Dockerfile'

# Drapeaux npm qui excluent les devDependencies de l'installation.
DEV_OMITTING_FLAGS = ('--only=production', '--omit=dev', '--production')


def npm_install_commands(dockerfile: Path) -> list:
    """Lignes `RUN npm ci|install` d'un Dockerfile, drapeaux compris."""
    return [
        line.strip()
        for line in dockerfile.read_text(encoding='utf-8').splitlines()
        if re.match(r'\s*RUN\s+npm\s+(ci|install)\b', line)
    ]


@pytest.mark.parametrize('dockerfile', [DOCKERFILE_PROD, WEB_DOCKERFILE],
                         ids=['Dockerfile.prod', 'web/Dockerfile'])
def test_le_builder_web_installe_les_devdependencies(dockerfile):
    commands = npm_install_commands(dockerfile)
    assert commands, f"aucune installation npm trouvée dans {dockerfile.name}"
    for command in commands:
        for flag in DEV_OMITTING_FLAGS:
            assert flag not in command, (
                f"{dockerfile.name} : « {command} » exclut les devDependencies, "
                f"or `next build` type-check les fichiers qui les importent "
                f"(vitest.config.ts, *.test.tsx) — le build échouera."
            )


def test_les_fichiers_de_test_web_importent_bien_des_devdependencies():
    """Verrouille la prémisse des tests ci-dessus : si plus aucun fichier
    type-checké n'importait de devDependency, la contrainte n'aurait plus
    lieu d'être et ces tests deviendraient du bruit."""
    web = REPO_ROOT / 'web'
    importers = [
        path for path in list(web.glob('*.ts')) + list(web.glob('app/**/*.test.ts*'))
        if re.search(r"from '(vitest|@testing-library/|@vitejs/)",
                     path.read_text(encoding='utf-8'))
    ]
    assert importers, (
        "aucun fichier type-checké n'importe de devDependency : revoir la "
        "nécessité de test_le_builder_web_installe_les_devdependencies"
    )


@pytest.mark.integration
def test_le_stage_web_builder_se_construit_reellement():
    """Seul ce test attrape réellement la classe de bug : les assertions texte
    ci-dessus ne voient qu'un drapeau, pas un `next build` qui échoue."""
    result = subprocess.run(
        ['docker', 'build', '--target', 'web-builder',
         '-f', str(DOCKERFILE_PROD), str(REPO_ROOT)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr[-4000:]
