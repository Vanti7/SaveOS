"""
SaveOS - Système de Sauvegarde Centralisé
API principale - Gère l'authentification, les agents, et les jobs de sauvegarde

Copyright (C) 2024 SaveOS Project
Licensed under GNU Affero General Public License v3.0 (AGPL-3.0)
See LICENSE file for details.
"""
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import json

from api.database import get_db, create_tables, Agent, Job, Snapshot, Tenant
from api.schemas import (
    AgentRegister, AgentResponse, AgentHeartbeat, AgentStats,
    JobCreate, JobResponse, SnapshotResponse
)
from api.auth import AuthManager, get_current_agent
from worker.tasks import enqueue_backup_job

# Configuration
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

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
async def metrics():
    """Métriques Prometheus basiques"""
    # TODO: Implémenter les métriques Prometheus
    return {"agents_total": 0, "jobs_total": 0}

# === ENDPOINTS AGENTS ===

@app.post(f"{API_PREFIX}/agents/register", response_model=AgentResponse)
async def register_agent(
    agent_data: AgentRegister,
    db: Session = Depends(get_db)
):
    """Enregistre un nouvel agent de sauvegarde"""
    
    # Vérifier si l'agent existe déjà (par hostname)
    existing_agent = db.query(Agent).filter(
        Agent.hostname == agent_data.hostname
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
    
    # Créer un tenant par défaut si aucun n'existe
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(name="default", quota_bytes=10000000000)  # 10GB
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
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
    snapshots = db.query(Snapshot).join(Job).filter(
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
    
    # Créer le job
    new_job = Job(
        agent_id=current_agent.id,
        type=job_data.type.value,
        config=str(job_data.config) if job_data.config else None,
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
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """Liste les snapshots d'un agent"""
    
    # Vérifier que l'agent demande ses propres snapshots
    if agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut consulter que ses propres snapshots"
        )
    
    # Récupérer les snapshots
    snapshots = db.query(Snapshot).join(Job).filter(
        Job.agent_id == agent_id
    ).order_by(Snapshot.created_at.desc()).all()
    
    return snapshots

@app.get(f"{API_PREFIX}/jobs/{{job_id}}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db)
):
    """Récupère le statut d'un job"""
    
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job non trouvé"
        )
    
    # Vérifier que l'agent demande ses propres jobs
    if job.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut consulter que ses propres jobs"
        )
    
    return job

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

@app.post("/api/v1/agents/provision")
async def provision_agent(
    hostname: str,
    platform: str,
    db: Session = Depends(get_db)
):
    """Provisionne un nouvel agent avec token pré-généré"""
    
    # Créer un tenant par défaut si aucun n'existe
    tenant = db.query(Tenant).first()
    if not tenant:
        tenant = Tenant(name="default", quota_bytes=10000000000)  # 10GB
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
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

def generate_agent_package(platform: str) -> bytes:
    """Génère un package d'installation pour la plateforme donnée"""
    import tempfile
    import zipfile
    import tarfile
    import io
    
    # Code de l'agent Python
    agent_code = '''#!/usr/bin/env python3
"""
SaveOS Agent - Client de sauvegarde
"""
import os
import sys
import json
import requests
import subprocess
import platform as plt
import argparse
from pathlib import Path
from datetime import datetime

class SaveOSAgent:
    def __init__(self, config_path=None):
        self.config_path = config_path or self.get_default_config_path()
        self.config = self.load_config()
        
    def get_default_config_path(self):
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get("APPDATA", "")) / "SaveOS"
        elif sys.platform == 'darwin':  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / "SaveOS"
        else:  # Linux
            config_dir = Path.home() / ".config" / "saveos"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"
    
    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config):
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def register(self, api_url=None, token=None):
        """Enregistre l'agent auprès du serveur"""
        if api_url:
            self.config['api_url'] = api_url
        if token:
            self.config['token'] = token
            
        self.config.update({
            'hostname': plt.node(),
            'platform': plt.system().lower(),
            'last_registration': datetime.now().isoformat()
        })
        
        self.save_config(self.config)
        print(f"✅ Agent enregistré auprès de {self.config.get('api_url')}")
        
        # Envoyer un heartbeat initial
        self.heartbeat()
    
    def heartbeat(self):
        """Envoie un heartbeat au serveur"""
        if not self.config.get('token'):
            print("❌ Token manquant. Enregistrez l'agent d'abord.")
            return
            
        try:
            response = requests.post(
                f"{self.config['api_url']}/api/v1/agents/heartbeat",
                json={"status": "active", "config": {}},
                headers={"Authorization": f"Bearer {self.config['token']}"},
                verify=False,
                timeout=30
            )
            if response.status_code == 200:
                print("💓 Heartbeat envoyé avec succès")
            else:
                print(f"❌ Erreur heartbeat: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
    
    def backup(self, paths=None):
        """Lance une sauvegarde"""
        if not self.config.get('token'):
            print("❌ Token manquant. Enregistrez l'agent d'abord.")
            return
            
        print("🚀 Lancement de la sauvegarde...")
        
        # Créer un job de sauvegarde
        try:
            response = requests.post(
                f"{self.config['api_url']}/api/v1/backup",
                json={
                    "agent_id": 1,  # Sera récupéré dynamiquement
                    "type": "backup",
                    "config": {
                        "source_paths": paths or [str(Path.home() / "Documents")],
                        "repo_path": str(Path.home() / ".saveos" / "repo"),
                        "passphrase": "default_passphrase_change_me"
                    }
                },
                headers={"Authorization": f"Bearer {self.config['token']}"},
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                job = response.json()
                print(f"✅ Job de sauvegarde créé (ID: {job['id']})")
            else:
                print(f"❌ Erreur lors de la création du job: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    def status(self):
        """Affiche le statut de l'agent"""
        print("📊 Status de l'agent SaveOS:")
        print(f"   Hostname: {self.config.get('hostname', 'Non configuré')}")
        print(f"   Platform: {self.config.get('platform', 'Non configuré')}")
        print(f"   API URL: {self.config.get('api_url', 'Non configuré')}")
        print(f"   Token: {'Configuré' if self.config.get('token') else 'Non configuré'}")
        print(f"   Config: {self.config_path}")
    
    def daemon(self):
        """Démarre l'agent en mode daemon"""
        import time
        print("🔄 Démarrage du daemon SaveOS Agent...")
        
        try:
            while True:
                self.heartbeat()
                time.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            print("\\n🛑 Arrêt du daemon")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SaveOS Agent')
    parser.add_argument('command', choices=['register', 'backup', 'status', 'daemon', 'heartbeat'])
    parser.add_argument('--api-url', help='URL de l\\'API SaveOS')
    parser.add_argument('--token', help='Token d\\'authentification')
    parser.add_argument('--paths', nargs='+', help='Chemins à sauvegarder')
    
    args = parser.parse_args()
    
    agent = SaveOSAgent()
    
    if args.command == 'register':
        agent.register(args.api_url, args.token)
    elif args.command == 'backup':
        agent.backup(args.paths)
    elif args.command == 'status':
        agent.status()
    elif args.command == 'daemon':
        agent.daemon()
    elif args.command == 'heartbeat':
        agent.heartbeat()
'''

    requirements = '''requests>=2.31.0
borgbackup>=1.2.6
'''

    # Scripts d'installation selon la plateforme
    if platform == 'windows':
        install_script = '''@echo off
echo 🚀 Installation de SaveOS Agent pour Windows...

REM Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python non trouvé. Veuillez installer Python 3.8+
    pause
    exit /b 1
)

REM Créer le répertoire d'installation
set INSTALL_DIR=%PROGRAMFILES%\\SaveOS
mkdir "%INSTALL_DIR%" 2>nul

REM Copier les fichiers
copy "agent.py" "%INSTALL_DIR%\\" >nul
copy "requirements.txt" "%INSTALL_DIR%\\" >nul

REM Créer le répertoire de configuration
mkdir "%APPDATA%\\SaveOS" 2>nul
copy "config.json" "%APPDATA%\\SaveOS\\" >nul

REM Installer les dépendances
cd /d "%INSTALL_DIR%"
python -m pip install -r requirements.txt

REM Enregistrer l'agent
python agent.py register

echo ✅ Installation terminée!
echo L'agent SaveOS est maintenant installé.
pause
'''
    else:
        install_script = '''#!/bin/bash
echo "🚀 Installation de SaveOS Agent..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trouvé. Installation..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install python@3.11
        else
            echo "Veuillez installer Homebrew: https://brew.sh"
            exit 1
        fi
    else
        # Linux
        sudo apt-get update && sudo apt-get install -y python3 python3-pip
    fi
fi

# Créer le répertoire d'installation
INSTALL_DIR="/opt/saveos"
sudo mkdir -p "$INSTALL_DIR"
sudo cp agent.py "$INSTALL_DIR/"
sudo cp requirements.txt "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/agent.py"

# Configuration utilisateur
if [[ "$OSTYPE" == "darwin"* ]]; then
    CONFIG_DIR="$HOME/Library/Application Support/SaveOS"
else
    CONFIG_DIR="$HOME/.config/saveos"
fi

mkdir -p "$CONFIG_DIR"
cp config.json "$CONFIG_DIR/"

# Installer les dépendances
cd "$INSTALL_DIR"
sudo python3 -m pip install -r requirements.txt

# Enregistrer l'agent
python3 agent.py register

echo "✅ Installation terminée!"
echo "L'agent SaveOS est maintenant installé."
'''

    # Configuration par défaut
    config = {
        "api_url": f"https://{os.getenv('API_HOST', 'localhost')}:{os.getenv('API_PORT', '8000')}",
        "hostname": f"{platform}-agent",
        "platform": platform,
        "verify_ssl": False,
        "heartbeat_interval": 300
    }

    # Créer le package
    if platform == 'windows':
        # Package ZIP pour Windows
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('agent.py', agent_code)
            zf.writestr('requirements.txt', requirements)
            zf.writestr('install.bat', install_script)
            zf.writestr('config.json', json.dumps(config, indent=2))
            zf.writestr('README.txt', f'SaveOS Agent pour {platform}\\n\\nExécutez install.bat pour installer.')
        
        return buffer.getvalue()
    else:
        # Package TAR.GZ pour Unix
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as tf:
            
            def add_string(name, content):
                info = tarfile.TarInfo(name=name)
                info.size = len(content.encode())
                info.mode = 0o755 if name.endswith('.sh') else 0o644
                tf.addfile(info, io.BytesIO(content.encode()))
            
            add_string('agent.py', agent_code)
            add_string('requirements.txt', requirements)
            add_string('install.sh', install_script)
            add_string('config.json', json.dumps(config, indent=2))
            add_string('README.md', f'# SaveOS Agent pour {platform}\\n\\nExécutez `bash install.sh` pour installer.')
        
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