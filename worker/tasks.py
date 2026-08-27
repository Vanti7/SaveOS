"""
Tâches de traitement pour le worker SaveOS
"""
import os
import json
import shutil
import subprocess
import tempfile
import threading
import time
from wsgiref.simple_server import make_server
from datetime import datetime
from typing import Dict, Any, List, Optional
import redis
from rq import Queue, Worker, Connection
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from prometheus_client import Counter, Histogram, CollectorRegistry, multiprocess, make_wsgi_app

from api.database import Job, Snapshot, Agent, Tenant

# Configuration Redis et base de données
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://saveos:saveos123@localhost:5432/saveos")

DEFAULT_BORG_PASSPHRASE = "default_passphrase_change_me"
RESTORE_PACKAGE_DIR = os.getenv("RESTORE_PACKAGE_DIR", "/tmp/restore_packages")
WORKER_METRICS_PORT = int(os.getenv("WORKER_METRICS_PORT", "9200"))

# Métriques Prometheus événementielles (le worker est un process long-lived,
# contrairement à l'API — voir api/main.py pour les jauges dérivées de la DB).
WORKER_JOBS_TOTAL = Counter(
    'saveos_worker_jobs_total', 'Jobs traités par le worker', ['job_type', 'outcome']
)
WORKER_JOB_DURATION = Histogram(
    'saveos_worker_job_duration_seconds', 'Durée de traitement des jobs', ['job_type']
)


def _record_job_metrics(job_type: str, outcome: str, duration_seconds: float) -> None:
    WORKER_JOBS_TOTAL.labels(job_type=job_type, outcome=outcome).inc()
    WORKER_JOB_DURATION.labels(job_type=job_type).observe(duration_seconds)

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
    
    def prune(self, retention: Dict[str, int]) -> Dict[str, Any]:
        """Purge les anciennes archives selon une politique de rétention
        (clés reconnues : daily/weekly/monthly, voir Tenant.retention_policy
        et docs/adr/0006-facturation-quotas.md). N'appelle borg que pour les
        clés effectivement présentes dans retention."""
        flag_by_key = {'daily': '--keep-daily', 'weekly': '--keep-weekly', 'monthly': '--keep-monthly'}
        try:
            cmd = ['borg', 'prune', '--list']
            for key, flag in flag_by_key.items():
                if key in retention:
                    cmd += [flag, str(retention[key])]
            cmd.append(self.repo_path)

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

    def list_archive_contents(self, archive_name: str) -> Dict[str, Any]:
        """Liste le contenu (fichiers/dossiers) d'une archive Borg"""
        try:
            archive_path = f"{self.repo_path}::{archive_name}"
            cmd = ['borg', 'list', '--json-lines', archive_path]
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                check=False
            )

            entries = []
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    entries.append({
                        'path': entry.get('path'),
                        'type': entry.get('type'),
                        'size': entry.get('size'),
                        'mtime': entry.get('mtime'),
                    })

            return {
                'success': result.returncode == 0,
                'entries': entries,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def extract(self, archive_name: str, target_dir: str, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Extrait une archive (ou des chemins précis de celle-ci) vers target_dir"""
        try:
            os.makedirs(target_dir, exist_ok=True)
            archive_path = f"{self.repo_path}::{archive_name}"
            cmd = ['borg', 'extract', archive_path] + (paths or [])

            result = subprocess.run(
                cmd,
                env=self.env,
                cwd=target_dir,
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


def _reconcile_pruned_snapshots(db, borg: 'BorgManager', repo_path: str) -> None:
    """Après un borg prune réussi, aligne la base sur les archives réellement
    restantes : supprime les Snapshot dont l'archive a été purgée (met
    d'abord à NULL tout Job.snapshot_id qui y référence — colonne utilisée
    à la fois pour le snapshot produit par un backup et pour le snapshot
    source d'une restauration, contrainte FK sur snapshots.id).

    Garde-fou : une liste d'archives vide n'entraîne aucune suppression
    (évite un effacement en masse en cas d'anomalie de parsing côté Borg)."""
    list_result = borg.list_archives()
    if not list_result.get('success'):
        return

    current_names = {a['name'] for a in list_result['archives']}
    if not current_names:
        return

    stale_snapshots = db.query(Snapshot).filter(
        Snapshot.repo_path == repo_path,
        ~Snapshot.name.in_(current_names)
    ).all()

    if not stale_snapshots:
        return

    for snapshot in stale_snapshots:
        db.query(Job).filter(Job.snapshot_id == snapshot.id).update({'snapshot_id': None})
        db.delete(snapshot)
    db.commit()


def process_backup_job(job_id: int) -> Dict[str, Any]:
    """Traite un job de sauvegarde"""
    
    db = SessionLocal()
    result = {'success': False, 'message': ''}
    start_time = None

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
        start_time = time.monotonic()

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
        passphrase = config.get('passphrase', DEFAULT_BORG_PASSPHRASE)
        
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
                _record_job_metrics('backup', 'failure', time.monotonic() - start_time)
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

            # Purge des anciens snapshots selon la politique de rétention du
            # tenant (voir docs/adr/0006-facturation-quotas.md). Ne doit
            # jamais faire échouer un backup déjà réussi : erreurs ignorées.
            try:
                tenant = db.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
                retention = json.loads(tenant.retention_policy) if tenant and tenant.retention_policy else {}
                recognized_retention = {k: v for k, v in retention.items() if k in ('daily', 'weekly', 'monthly')}
                if recognized_retention:
                    prune_result = borg.prune(recognized_retention)
                    if prune_result.get('success'):
                        _reconcile_pruned_snapshots(db, borg, repo_path)
            except Exception:
                pass

            result['success'] = True
            result['message'] = f"Sauvegarde réussie: {archive_name}"
            result['snapshot_id'] = snapshot.id
            result['size_bytes'] = size_bytes
            _record_job_metrics('backup', 'success', time.monotonic() - start_time)

        else:
            # Échec de la sauvegarde
            job.status = "failed"
            job.error_message = backup_result.get('stderr', backup_result.get('error', 'Erreur inconnue'))
            job.finished_at = datetime.utcnow()
            db.commit()
            _record_job_metrics('backup', 'failure', time.monotonic() - start_time)

            result['message'] = f"Échec de la sauvegarde: {job.error_message}"

    except Exception as e:
        # Erreur générale
        if 'job' in locals():
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
        if start_time is not None:
            _record_job_metrics('backup', 'failure', time.monotonic() - start_time)

        result['message'] = f"Erreur lors du traitement du job: {str(e)}"

    finally:
        db.close()

    return result

def enqueue_backup_job(job_id: int) -> str:
    """Ajoute un job de sauvegarde à la queue"""
    job = queue.enqueue(
        process_backup_job,
        job_id,
        job_timeout='1h'
    )
    return job.id

def process_restore_job(job_id: int) -> Dict[str, Any]:
    """Traite un job de restauration : extrait les chemins sélectionnés d'un
    snapshot puis les empaquette en zip, prêt à être téléchargé (target=download)
    ou récupéré par l'agent (target=agent)."""

    db = SessionLocal()
    result = {'success': False, 'message': ''}
    extract_dir = None
    start_time = None

    try:
        # Récupérer le job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            result['message'] = f"Job {job_id} non trouvé"
            return result

        # Marquer le job comme en cours
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        start_time = time.monotonic()

        # Parser la configuration du job
        config = {}
        if job.config:
            try:
                config = json.loads(job.config)
            except (json.JSONDecodeError, TypeError):
                pass

        snapshot_id = config.get('snapshot_id')
        selected_paths = config.get('selected_paths') or []
        target = config.get('target', 'download')
        passphrase = config.get('passphrase', DEFAULT_BORG_PASSPHRASE)

        # Récupérer le snapshot source (repo/archive viennent de là, pas de défauts)
        snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            job.status = "failed"
            job.error_message = f"Snapshot {snapshot_id} non trouvé"
            job.finished_at = datetime.utcnow()
            db.commit()
            _record_job_metrics('restore', 'failure', time.monotonic() - start_time)
            result['message'] = job.error_message
            return result

        job.snapshot_id = snapshot.id
        db.commit()

        borg = BorgManager(snapshot.repo_path, passphrase)

        # Extraire les chemins sélectionnés vers un dossier temporaire
        extract_dir = tempfile.mkdtemp(prefix=f"restore_{job_id}_")
        extract_result = borg.extract(snapshot.name, extract_dir, selected_paths or None)

        if not extract_result['success']:
            job.status = "failed"
            job.error_message = extract_result.get('stderr', extract_result.get('error', 'Erreur inconnue'))
            job.finished_at = datetime.utcnow()
            db.commit()
            _record_job_metrics('restore', 'failure', time.monotonic() - start_time)
            result['message'] = f"Échec de l'extraction: {job.error_message}"
            return result

        # Empaqueter le résultat en zip sur le volume partagé
        os.makedirs(RESTORE_PACKAGE_DIR, exist_ok=True)
        package_base = os.path.join(RESTORE_PACKAGE_DIR, str(job_id))
        package_path = shutil.make_archive(package_base, 'zip', extract_dir)

        config['package_path'] = package_path
        job.config = json.dumps(config)

        if target == 'agent':
            # Le paquet est prêt : en attente de récupération par l'agent
            job.status = "ready_for_agent"
        else:
            job.status = "completed"
            job.finished_at = datetime.utcnow()

        db.commit()

        result['success'] = True
        result['message'] = f"Extraction réussie: {package_path}"
        result['package_path'] = package_path
        _record_job_metrics('restore', 'success', time.monotonic() - start_time)

    except Exception as e:
        # Erreur générale
        if 'job' in locals():
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
        if start_time is not None:
            _record_job_metrics('restore', 'failure', time.monotonic() - start_time)

        result['message'] = f"Erreur lors du traitement du job de restauration: {str(e)}"

    finally:
        if extract_dir:
            shutil.rmtree(extract_dir, ignore_errors=True)
        db.close()

    return result

def enqueue_restore_job(job_id: int) -> str:
    """Ajoute un job de restauration à la queue"""
    job = queue.enqueue(
        process_restore_job,
        job_id,
        job_timeout='1h'
    )
    return job.id

def _start_metrics_server(port: int) -> None:
    """Sert /metrics en agrégeant les fichiers multiprocess (voir worker/run.py :
    chaque job RQ s'exécute dans un processus enfant forké — os.fork() dans
    Worker.fork_work_horse —, dont les métriques n'existent que dans
    PROMETHEUS_MULTIPROC_DIR ; un CollectorRegistry standard ne verrait que
    celles du process parent, jamais celles des enfants déjà terminés)."""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    app = make_wsgi_app(registry)
    httpd = make_server('', port, app)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

def start_worker():
    """Démarre le worker RQ"""
    _start_metrics_server(WORKER_METRICS_PORT)
    print(f"Métriques Prometheus exposées sur :{WORKER_METRICS_PORT}/metrics")
    with Connection(redis_conn):
        worker = Worker([queue])
        print("Worker SaveOS démarré - En attente de jobs...")
        worker.work()