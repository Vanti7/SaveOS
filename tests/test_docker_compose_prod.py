"""
Tests structurels pour docker-compose.prod.yml : préviennent la régression
vers l'état "Traefik/Let's Encrypt déclarés mais jamais câblés au trafic
réel" (voir docs/adr/0003-certificats-tls-production.md). Assertions texte
simples, sans dépendance PyYAML (absente de requirements.txt) — limite
assumée : ne détecte pas les erreurs de structure YAML elles-mêmes, voir
le test @integration ci-dessous qui shell-out vers `docker compose config`
pour ça.
"""
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / 'docker-compose.prod.yml'


@pytest.fixture
def compose_text():
    return COMPOSE_FILE.read_text(encoding='utf-8')


def test_api_and_web_have_traefik_tls_labels(compose_text):
    assert 'traefik.http.routers.api.rule=Host(`api.${DOMAIN}`)' in compose_text
    assert 'traefik.http.routers.api.tls.certresolver=letsencrypt' in compose_text
    assert 'traefik.http.routers.web.rule=Host(`app.${DOMAIN}`)' in compose_text
    assert 'traefik.http.routers.web.tls.certresolver=letsencrypt' in compose_text


def test_api_web_and_dashboard_ports_not_published_to_host(compose_text):
    assert '"8000:8000"' not in compose_text
    assert '"3000:3000"' not in compose_text
    assert '"8080:8080"' not in compose_text


def test_api_and_web_do_not_set_a_fixed_container_name(compose_text):
    # container_name fixe + deploy.replicas > 1 est un projet compose invalide.
    assert 'container_name: saveos_api_prod' not in compose_text
    assert 'container_name: saveos_web_prod' not in compose_text


@pytest.mark.integration
def test_docker_compose_prod_config_is_structurally_valid():
    """Seul ce test attrape réellement la classe de bug container_name/replicas :
    les assertions texte ci-dessus ne voient pas les erreurs de structure YAML."""
    env = {
        **os.environ,
        'DOMAIN': 'example.com',
        'ACME_EMAIL': 'ops@example.com',
        'POSTGRES_PASSWORD': 'x',
        'MINIO_ROOT_USER': 'x',
        'MINIO_ROOT_PASSWORD': 'x',
        'MINIO_BROWSER_REDIRECT_URL': 'http://x',
        'DASHBOARD_API_TOKEN': 'x',
        'DATABASE_URL': 'postgresql://x',
        'REDIS_URL': 'redis://x',
        'MINIO_URL': 'http://x',
    }
    result = subprocess.run(
        ['docker', 'compose', '-f', str(COMPOSE_FILE), 'config', '--quiet'],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
