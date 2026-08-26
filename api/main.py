"""
SaveOS - Système de Sauvegarde Centralisé
API principale - Gère l'authentification, les agents, et les jobs de sauvegarde

Copyright (C) 2024 SaveOS Project
Licensed under GNU Affero General Public License v3.0 (AGPL-3.0)
See LICENSE file for details.
"""
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import json
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

from api.database import get_db, create_tables, Agent, Job, Snapshot, Tenant
from api.schemas import (
    AgentRegister, AgentResponse, AgentHeartbeat, AgentStats,
    JobCreate, JobResponse, JobType, SnapshotResponse,
    TenantCreate, TenantResponse, TenantCreateResponse
)
from api.auth import AuthManager, get_current_agent, get_current_principal, require_dashboard, Principal
from api.routers.restore import router as restore_router
from worker.tasks import enqueue_backup_job

# Configuration
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Métriques Prometheus : jauges recalculées depuis la DB à chaque scrape
# (l'API est sans état partagé entre process/replicas, donc pas de compteurs
# en mémoire côté API — voir worker/tasks.py pour les compteurs événementiels).
AGENTS_GAUGE = Gauge('saveos_agents_total', "Nombre d'agents par statut", ['status'])
JOBS_GAUGE = Gauge('saveos_jobs_total', 'Nombre de jobs par type et statut', ['type', 'status'])
SNAPSHOTS_GAUGE = Gauge('saveos_snapshots_total', 'Nombre total de snapshots')
SNAPSHOTS_SIZE_GAUGE = Gauge('saveos_snapshots_size_bytes_total', 'Taille totale des snapshots en octets')

# Initialisation FastAPI
app = FastAPI(
    title="SaveOS API",
    description="API pour système de sauvegarde centralisé avec agents multiplateforme",
    version="1.0.0"
)

# Configuration CORS pour le développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(restore_router, prefix=API_PREFIX, tags=["restore"])

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    create_tables()
    print("SaveOS API démarrée - Tables créées")

@app.get("/health")
async def health_check():
    """Point de santé pour monitoring"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def metrics(db: Session = Depends(get_db)):
    """Métriques Prometheus (format d'exposition texte)"""

    # .clear() avant repeuplement : évite de garder indéfiniment une
    # combinaison de labels qui n'a plus aucune ligne correspondante en DB.
    AGENTS_GAUGE.clear()
    for status_value, count in db.query(Agent.status, func.count(Agent.id)).group_by(Agent.status).all():
        AGENTS_GAUGE.labels(status=status_value).set(count)

    JOBS_GAUGE.clear()
    for type_value, status_value, count in db.query(Job.type, Job.status, func.count(Job.id)).group_by(Job.type, Job.status).all():
        JOBS_GAUGE.labels(type=type_value, status=status_value).set(count)

    SNAPSHOTS_GAUGE.set(db.query(func.count(Snapshot.id)).scalar() or 0)
    SNAPSHOTS_SIZE_GAUGE.set(db.query(func.coalesce(func.sum(Snapshot.size_bytes), 0)).scalar() or 0)

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# === ENDPOINTS AGENTS ===

@app.post(f"{API_PREFIX}/agents/register", response_model=AgentResponse)
async def register_agent(
    agent_data: AgentRegister,
    db: Session = Depends(get_db)
):
    """Enregistre un nouvel agent de sauvegarde, rattaché au tenant identifié
    par le secret d'enregistrement (voir docs/adr/0004-multi-tenancy-avancee.md)."""

    tenant = AuthManager.verify_registration_secret(db, agent_data.registration_secret)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Secret d'enregistrement invalide"
        )

    # Vérifier si l'agent existe déjà (par hostname, dans ce tenant uniquement)
    existing_agent = db.query(Agent).filter(
        Agent.tenant_id == tenant.id, Agent.hostname == agent_data.hostname
    ).first()

    if existing_agent:
        # Mettre à jour l'agent existant
        existing_agent.platform = agent_data.platform
        existing_agent.config = str(agent_data.config) if agent_data.config else None
        existing_agent.last_seen = datetime.utcnow()
        existing_agent.status = "active"
        db.commit()
        db.refresh(existing_agent)
        return existing_agent

    # Générer un token pour le nouvel agent
    token = AuthManager.generate_agent_token()
    hashed_token = AuthManager.hash_token(token)
    
    # Créer le nouvel agent
    new_agent = Agent(
        tenant_id=tenant.id,
        hostname=agent_data.hostname,
        platform=agent_data.platform,
        token=hashed_token,
        config=str(agent_data.config) if agent_data.config else None,
        status="active"
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    # Retourner l'agent avec le token en clair (une seule fois)
    response = AgentResponse(
        id=new_agent.id,
        hostname=new_agent.hostname,
        platform=new_agent.platform,
        token=token,  # Token en clair pour la première fois
        status=new_agent.status,
        last_seen=new_agent.last_seen,
        created_at=new_agent.created_at
    )
    
    return response

@app.post(f"{API_PREFIX}/agents/heartbeat")
async def agent_heartbeat(
    heartbeat: AgentHeartbeat,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """Heartbeat de l'agent pour maintenir la connexion"""
    
    current_agent.status = heartbeat.status.value
    current_agent.last_seen = datetime.utcnow()
    
    if heartbeat.config:
        current_agent.config = str(heartbeat.config)
    
    db.commit()
    
    return {"message": "Heartbeat reçu", "timestamp": datetime.utcnow()}

@app.get(f"{API_PREFIX}/agents/stats", response_model=AgentStats)
async def get_agent_stats(
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques de l'agent"""
    
    # Compter les snapshots
    snapshots = db.query(Snapshot).join(Job, Snapshot.job_id == Job.id).filter(
        Job.agent_id == current_agent.id
    ).all()
    
    total_snapshots = len(snapshots)
    total_size_bytes = sum(s.size_bytes for s in snapshots)
    
    # Dernière sauvegarde
    last_job = db.query(Job).filter(
        Job.agent_id == current_agent.id,
        Job.type == "backup",
        Job.status == "completed"
    ).order_by(Job.finished_at.desc()).first()
    
    last_backup = last_job.finished_at if last_job else None
    
    return AgentStats(
        total_snapshots=total_snapshots,
        total_size_bytes=total_size_bytes,
        last_backup=last_backup,
        status=current_agent.status
    )

# === ENDPOINTS JOBS ===

@app.post(f"{API_PREFIX}/backup", response_model=JobResponse)
async def create_backup_job(
    job_data: JobCreate,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """Lance un job de sauvegarde"""
    
    # Vérifier que l'agent demande un job pour lui-même
    if job_data.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut créer des jobs que pour lui-même"
        )

    # Quota de stockage du tenant : vérifie l'espace déjà consommé par les
    # sauvegardes terminées (pas la taille du job à venir, impossible à
    # connaître à l'avance) — simplification assumée, voir
    # docs/adr/0004-multi-tenancy-avancee.md. Ne s'applique qu'aux backups.
    if job_data.type == JobType.BACKUP:
        tenant = db.query(Tenant).filter(Tenant.id == current_agent.tenant_id).first()
        consumed_bytes = (
            db.query(func.coalesce(func.sum(Snapshot.size_bytes), 0))
            .join(Job, Snapshot.job_id == Job.id)
            .join(Agent, Job.agent_id == Agent.id)
            .filter(Agent.tenant_id == tenant.id)
            .scalar()
        )
        if consumed_bytes >= tenant.quota_bytes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Quota de stockage du tenant dépassé"
            )

    # Créer le job
    new_job = Job(
        agent_id=current_agent.id,
        type=job_data.type.value,
        config=json.dumps(job_data.config) if job_data.config else None,
        status="pending"
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Envoyer le job dans la queue Redis
    try:
        enqueue_backup_job(new_job.id)
    except Exception as e:
        # En cas d'erreur, marquer le job comme failed
        new_job.status = "failed"
        new_job.error_message = f"Erreur lors de l'ajout à la queue: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du job"
        )
    
    return new_job

@app.get(f"{API_PREFIX}/backup/{{agent_id}}/snapshots", response_model=List[SnapshotResponse])
async def list_agent_snapshots(
    agent_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """Liste les snapshots d'un agent"""

    # Un agent ne peut consulter que ses propres snapshots ; le tableau de
    # bord peut consulter ceux de n'importe quel agent.
    if not principal.can_act_on_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut consulter que ses propres snapshots"
        )

    # Récupérer les snapshots (agent_id n'est pas une colonne de Snapshot,
    # il vient du job qui l'a produit)
    snapshots = db.query(Snapshot).join(Job, Snapshot.job_id == Job.id).filter(
        Job.agent_id == agent_id
    ).order_by(Snapshot.created_at.desc()).all()

    return [
        SnapshotResponse(
            id=s.id, job_id=s.job_id, agent_id=agent_id, name=s.name,
            repo_path=s.repo_path, size_bytes=s.size_bytes, is_full=s.is_full,
            checksum=s.checksum, created_at=s.created_at,
        )
        for s in snapshots
    ]

@app.get(f"{API_PREFIX}/jobs/{{job_id}}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db)
):
    """Récupère le statut d'un job"""

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trouvé"
        )

    # Un agent ne peut consulter que ses propres jobs ; le tableau de bord
    # peut consulter ceux de n'importe quel agent.
    if not principal.can_act_on_agent(job.agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut consulter que ses propres jobs"
        )

    return job

# === ENDPOINTS TABLEAU DE BORD (liste-tout, réservés au dashboard) ===

@app.get(f"{API_PREFIX}/agents", response_model=List[AgentResponse])
async def list_all_agents(
    tenant_id: Optional[int] = None,
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Liste les agents (tableau de bord uniquement), tous tenants confondus
    si tenant_id est omis (vue super-admin), sinon filtrés par tenant."""
    query = db.query(Agent)
    if tenant_id is not None:
        query = query.filter(Agent.tenant_id == tenant_id)
    return query.order_by(Agent.created_at.desc()).all()

@app.get(f"{API_PREFIX}/jobs", response_model=List[JobResponse])
async def list_all_jobs(
    agent_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Liste tous les jobs, éventuellement filtrés par agent et/ou tenant (tableau de bord uniquement)"""
    query = db.query(Job)
    if agent_id is not None:
        query = query.filter(Job.agent_id == agent_id)
    if tenant_id is not None:
        query = query.join(Agent, Job.agent_id == Agent.id).filter(Agent.tenant_id == tenant_id)
    return query.order_by(Job.created_at.desc()).all()

@app.get(f"{API_PREFIX}/snapshots", response_model=List[SnapshotResponse])
async def list_all_snapshots(
    tenant_id: Optional[int] = None,
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Liste les snapshots (tableau de bord uniquement), tous tenants
    confondus si tenant_id est omis, sinon filtrés par tenant."""
    query = (
        db.query(Snapshot, Job.agent_id)
        .join(Job, Snapshot.job_id == Job.id)
    )
    if tenant_id is not None:
        query = query.join(Agent, Job.agent_id == Agent.id).filter(Agent.tenant_id == tenant_id)
    rows = query.order_by(Snapshot.created_at.desc()).all()
    return [
        SnapshotResponse(
            id=s.id, job_id=s.job_id, agent_id=agent_id, name=s.name,
            repo_path=s.repo_path, size_bytes=s.size_bytes, is_full=s.is_full,
            checksum=s.checksum, created_at=s.created_at,
        )
        for s, agent_id in rows
    ]

# === ENDPOINTS TÉLÉCHARGEMENT D'AGENTS ===

@app.get("/download/agent/{platform}")
async def download_agent(platform: str):
    """Télécharge un package d'agent pour une plateforme donnée"""
    
    if platform not in ['windows', 'macos', 'linux']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plateforme non supportée"
        )
    
    # Générer le package d'agent
    agent_package = generate_agent_package(platform)
    
    # Déterminer le type de contenu et l'extension
    if platform == 'windows':
        content_type = 'application/zip'
        filename = f'saveos-agent-{platform}.zip'
    else:
        content_type = 'application/gzip'
        filename = f'saveos-agent-{platform}.tar.gz'
    
    return Response(
        content=agent_package,
        media_type=content_type,
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )

# Doit rester aligné avec les noms de fichiers produits par le job
# build-agent-installers de .github/workflows/release.yml.
_INSTALLER_ASSET_TEMPLATES = {
    'windows': 'SaveOS-Agent-Setup-{version}-windows.exe',
    'macos': 'SaveOS-Agent-{version}-macos.dmg',
    'linux': 'saveos-agent_{version}_amd64.deb',
}
_VERSION_FILE = Path(__file__).resolve().parent.parent / 'VERSION'

def _get_current_version() -> str:
    return _VERSION_FILE.read_text(encoding='utf-8').strip()

@app.get("/download/agent/{platform}/installer")
async def download_agent_installer(platform: str):
    """Redirige vers l'installeur natif (exe/dmg/deb) de la version
    courante, publié en asset sur la GitHub Release correspondante.
    L'API reste stateless : aucun binaire stocké ni proxyé ici — voir
    docs/adr/0002-packaging-agents.md."""

    if platform not in _INSTALLER_ASSET_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plateforme non supportée"
        )

    version = _get_current_version()
    repo = os.getenv('GITHUB_REPO', 'Vanti7/SaveOS')
    asset_name = _INSTALLER_ASSET_TEMPLATES[platform].format(version=version)

    return RedirectResponse(
        url=f"https://github.com/{repo}/releases/download/v{version}/{asset_name}",
        status_code=status.HTTP_302_FOUND,
    )

@app.post("/api/v1/agents/provision")
async def provision_agent(
    hostname: str,
    platform: str,
    tenant_id: int,
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Provisionne un nouvel agent avec token pré-généré, pour un tenant
    explicite. Réservé au tableau de bord (voir
    docs/adr/0004-multi-tenancy-avancee.md) : émettre un token d'agent
    valide sans authentification était une faille pré-existante."""

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant introuvable")

    if db.query(Agent).filter(Agent.tenant_id == tenant.id, Agent.hostname == hostname).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un agent avec ce hostname existe déjà pour ce tenant"
        )

    # Générer un token pour le nouvel agent
    token = AuthManager.generate_agent_token()
    hashed_token = AuthManager.hash_token(token)
    
    # Créer l'agent provisionné (pas encore actif)
    new_agent = Agent(
        tenant_id=tenant.id,
        hostname=hostname,
        platform=platform,
        token=hashed_token,
        status="inactive"  # Sera activé lors du premier heartbeat
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return {
        "agent_id": new_agent.id,
        "token": token,  # Token en clair pour la configuration
        "hostname": hostname,
        "platform": platform,
        "api_url": f"https://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', '8000')}"
    }

@app.post(f"{API_PREFIX}/tenants", response_model=TenantCreateResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Crée un tenant et retourne son secret d'enregistrement en clair, une
    seule fois (comme le token d'un agent) — réservé au tableau de bord."""

    secret = AuthManager.generate_agent_token()
    tenant = Tenant(
        name=tenant_data.name,
        quota_bytes=tenant_data.quota_bytes,
        registration_secret_hash=AuthManager.hash_token(secret)
    )
    if tenant_data.retention_policy is not None:
        tenant.retention_policy = json.dumps(tenant_data.retention_policy)

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return TenantCreateResponse(
        id=tenant.id,
        name=tenant.name,
        quota_bytes=tenant.quota_bytes,
        retention_policy=tenant.retention_policy,
        created_at=tenant.created_at,
        registration_secret=secret
    )

@app.get(f"{API_PREFIX}/tenants", response_model=List[TenantResponse])
async def list_tenants(
    _: None = Depends(require_dashboard),
    db: Session = Depends(get_db)
):
    """Liste les tenants (sans leur secret d'enregistrement) — réservé au tableau de bord."""
    return db.query(Tenant).order_by(Tenant.created_at.desc()).all()

AGENT_SOURCE_DIR = Path(__file__).resolve().parent.parent / 'agent'
AGENT_SOURCE_FILES = ['__init__.py', 'cli.py', 'config.py', 'api_client.py', 'service.py']

def generate_agent_package(platform: str) -> bytes:
    """Génère un package d'installation (code source) pour la plateforme
    donnée, à partir des vrais fichiers du package agent/ — plus de copie
    dupliquée et obsolète : ce qui est livré est ce qui tourne réellement
    en développement (mêmes commandes, y compris service/apply-restores).
    Pour un exécutable autonome sans dépendance Python, voir
    /download/agent/{platform}/installer (packaging/, construit par CI)."""
    import zipfile
    import tarfile
    import io

    # Dépendances minimales de l'agent (agent/, pas requirements.txt complet
    # de l'appli) — doit rester aligné avec setup.py::install_requires.
    requirements = "click>=8.1.7\nrequests>=2.31.0\npython-dotenv>=1.0.0\n"

    if platform == 'windows':
        install_script = '''@echo off
echo Installation de SaveOS Agent pour Windows...

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python non trouve. Veuillez installer Python 3.8+
    pause
    exit /b 1
)

set INSTALL_DIR=%PROGRAMFILES%\\SaveOS
mkdir "%INSTALL_DIR%" 2>nul
xcopy /E /I /Y agent "%INSTALL_DIR%\\agent" >nul
copy requirements.txt "%INSTALL_DIR%\\" >nul

mkdir "%APPDATA%\\SaveOS" 2>nul
copy config.json "%APPDATA%\\SaveOS\\" >nul

cd /d "%INSTALL_DIR%"
python -m pip install -r requirements.txt

python -m agent.cli register

echo Installation terminee !
echo L'agent SaveOS est maintenant installe.
pause
'''
    else:
        install_script = '''#!/bin/bash
set -e
echo "Installation de SaveOS Agent..."

if ! command -v python3 &> /dev/null; then
    echo "Python 3 non trouve. Installation..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install python@3.11
        else
            echo "Veuillez installer Homebrew: https://brew.sh"
            exit 1
        fi
    else
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
    fi
fi

INSTALL_DIR="/opt/saveos"
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r agent "$INSTALL_DIR/"
sudo cp requirements.txt "$INSTALL_DIR/"

if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/Library/Application Support/SaveOS"
else
    CONFIG_DIR="$HOME/.config/saveos"
fi

mkdir -p "$CONFIG_DIR"
cp config.json "$CONFIG_DIR/"

cd "$INSTALL_DIR"
sudo python3 -m pip install -r requirements.txt

python3 -m agent.cli register

echo "Installation terminee !"
echo "L'agent SaveOS est maintenant installe."
'''

    # False seulement pour localhost/127.0.0.1 (self-signed connu) — sinon
    # True, cohérent avec agent.config.AgentConfig._default_verify_ssl (pas
    # d'import croisé api/<->agent, AGENT.MD impose la séparation stricte).
    # Voir docs/adr/0003-certificats-tls-production.md.
    api_host = os.getenv('API_HOST', 'localhost')
    config = {
        "api_url": f"https://{api_host}:{os.getenv('API_PORT', '8000')}",
        "hostname": f"{platform}-agent",
        "platform": platform,
        "verify_ssl": api_host not in ("localhost", "127.0.0.1"),
        "heartbeat_interval": 300
    }

    if platform == 'windows':
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in AGENT_SOURCE_FILES:
                zf.write(AGENT_SOURCE_DIR / filename, arcname=f'agent/{filename}')
            zf.writestr('requirements.txt', requirements)
            zf.writestr('install.bat', install_script)
            zf.writestr('config.json', json.dumps(config, indent=2))
            zf.writestr('README.txt', f'SaveOS Agent pour {platform}\n\nExécutez install.bat pour installer.')

        return buffer.getvalue()
    else:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as tf:
            for filename in AGENT_SOURCE_FILES:
                tf.add(AGENT_SOURCE_DIR / filename, arcname=f'agent/{filename}')

            def add_string(name, content):
                info = tarfile.TarInfo(name=name)
                info.size = len(content.encode())
                info.mode = 0o755 if name.endswith('.sh') else 0o644
                tf.addfile(info, io.BytesIO(content.encode()))

            add_string('requirements.txt', requirements)
            add_string('install.sh', install_script)
            add_string('config.json', json.dumps(config, indent=2))
            add_string('README.md', f'# SaveOS Agent pour {platform}\n\nExécutez `bash install.sh` pour installer.')

        return buffer.getvalue()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile="certs/key.pem",
        ssl_certfile="certs/cert.pem"
    )