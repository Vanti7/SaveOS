"""
Tâches de traitement pour le worker SaveOS
"""
import os
import json
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
import redis
from rq import Queue, Worker, Connection
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from api.database import Job, Snapshot, Agent

# Configuration Redis et base de données
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saveos:saveos123@localhost:5432/saveos")

redis_conn = redis.from_url(REDIS_URL)
queue = Queue('saveos_jobs', connection=redis_conn)

# Configuration base de données pour le worker
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class BorgManager:
    """Gestionnaire des opérations Borg"""
    
    def __init__(self, repo_path: str, passphrase: str):
        self.repo_path = repo_path
        self.passphrase = passphrase
        self.env = {
            **os.environ,
            'BORG_PASSPHRASE': passphrase,
            'BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK': 'yes',
            'BORG_RELOCATED_REPO_ACCESS_IS_OK': 'yes'
        }
    
    def init_repo(self) -> Dict[str, Any]:
        """Initialise un nouveau repository Borg"""
        try:
            cmd = ['borg', 'init', '--encryption=repokey', self.repo_path]
            result = subprocess.run(
                cmd, 
                env=self.env,
                capture_output=True, 
                text=True, 
                check=False
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_backup(self, source_paths: list, archive_name: str) -> Dict[str, Any]:
        """Crée une sauvegarde Borg"""
        try:
            archive_path = f"{self.repo_path}::{archive_name}"
            cmd = ['borg', 'create', '--stats', '--progress', archive_path] + source_paths
            
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parser les statistiques de sortie
            stats = self._parse_borg_stats(result.stderr)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'stats': stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_archives(self) -> Dict[str, Any]:
        """Liste les archives du repository"""
        try:
            cmd = ['borg', 'list', '--json', self.repo_path]
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                check=False
            )
            
            archives = []
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                archives = data.get('archives', [])
            
            return {
                'success': result.returncode == 0,
                'archives': archives,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_borg_stats(self, stderr: str) -> Dict[str, Any]:
        """Parse les statistiques de sortie de Borg"""
        stats = {}
        
        for line in stderr.split('\n'):
            if 'Original size:' in line:
                try:
                    size_str = line.split(':')[1].strip().split()[0]
                    stats['original_size'] = self._parse_size(size_str)
                except:
                    pass
            elif 'Compressed size:' in line:
                try:
                    size_str = line.split(':')[1].strip().split()[0]
                    stats['compressed_size'] = self._parse_size(size_str)
                except:
                    pass
            elif 'Deduplicated size:' in line:
                try:
                    size_str = line.split(':')[1].strip().split()[0]
                    stats['deduplicated_size'] = self._parse_size(size_str)
                except:
                    pass
        
        return stats
    
    def _parse_size(self, size_str: str) -> int:
        """Parse une taille avec unité (ex: 1.2 MB) en bytes"""
        try:
            size_str = size_str.replace(',', '.')
            if 'KB' in size_str:
                return int(float(size_str.replace('KB', '')) * 1024)
            elif 'MB' in size_str:
                return int(float(size_str.replace('MB', '')) * 1024 * 1024)
            elif 'GB' in size_str:
                return int(float(size_str.replace('GB', '')) * 1024 * 1024 * 1024)
            elif 'TB' in size_str:
                return int(float(size_str.replace('TB', '')) * 1024 * 1024 * 1024 * 1024)
            else:
                return int(size_str.replace('B', ''))
        except:
            return 0

def process_backup_job(job_id: int) -> Dict[str, Any]:
    """Traite un job de sauvegarde"""
    
    db = SessionLocal()
    result = {'success': False, 'message': ''}
    
    try:
        # Récupérer le job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            result['message'] = f"Job {job_id} non trouvé"
            return result
        
        # Récupérer l'agent
        agent = db.query(Agent).filter(Agent.id == job.agent_id).first()
        if not agent:
            result['message'] = f"Agent {job.agent_id} non trouvé"
            return result
        
        # Marquer le job comme en cours
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Parser la configuration du job
        config = {}
        if job.config:
            try:
                config = json.loads(job.config)
            except:
                pass
        
        # Configuration par défaut
        source_paths = config.get('source_paths', ['/tmp/test'])  # Chemin par défaut pour test
        repo_path = config.get('repo_path', f'/tmp/borg_repos/{agent.hostname}')
        passphrase = config.get('passphrase', 'default_passphrase_change_me')
        
        # Créer le répertoire du repository s'il n'existe pas
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        
        # Initialiser le gestionnaire Borg
        borg = BorgManager(repo_path, passphrase)
        
        # Vérifier si le repository existe, sinon l'initialiser
        if not os.path.exists(repo_path):
            init_result = borg.init_repo()
            if not init_result['success']:
                job.status = "failed"
                job.error_message = f"Erreur lors de l'initialisation du repo: {init_result.get('stderr', init_result.get('error'))}"
                job.finished_at = datetime.utcnow()
                db.commit()
                result['message'] = job.error_message
                return result
        
        # Créer le nom de l'archive
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{agent.hostname}_{timestamp}"
        
        # Effectuer la sauvegarde
        backup_result = borg.create_backup(source_paths, archive_name)
        
        if backup_result['success']:
            # Créer l'entrée snapshot
            stats = backup_result.get('stats', {})
            size_bytes = stats.get('compressed_size', 0)
            
            snapshot = Snapshot(
                job_id=job.id,
                name=archive_name,
                repo_path=repo_path,
                size_bytes=size_bytes,
                is_full=True,  # Pour le MVP, toutes les sauvegardes sont full
                created_at=datetime.utcnow()
            )
            
            db.add(snapshot)
            
            # Mettre à jour le job
            job.status = "completed"
            job.finished_at = datetime.utcnow()
            job.snapshot_id = snapshot.id
            
            db.commit()
            db.refresh(snapshot)
            
            result['success'] = True
            result['message'] = f"Sauvegarde réussie: {archive_name}"
            result['snapshot_id'] = snapshot.id
            result['size_bytes'] = size_bytes
            
        else:
            # Échec de la sauvegarde
            job.status = "failed"
            job.error_message = backup_result.get('stderr', backup_result.get('error', 'Erreur inconnue'))
            job.finished_at = datetime.utcnow()
            db.commit()
            
            result['message'] = f"Échec de la sauvegarde: {job.error_message}"
        
    except Exception as e:
        # Erreur générale
        if 'job' in locals():
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
        
        result['message'] = f"Erreur lors du traitement du job: {str(e)}"
    
    finally:
        db.close()
    
    return result

def enqueue_backup_job(job_id: int) -> str:
    """Ajoute un job de sauvegarde à la queue"""
    job = queue.enqueue(
        process_backup_job,
        job_id,
        timeout='1h',  # Timeout de 1 heure
        job_timeout='1h'
    )
    return job.id

def start_worker():
    """Démarre le worker RQ"""
    with Connection(redis_conn):
        worker = Worker([queue])
        print("Worker SaveOS démarré - En attente de jobs...")
        worker.work()

if __name__ == '__main__':
    start_worker()