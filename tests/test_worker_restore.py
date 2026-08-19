"""
Tests pour les fonctionnalités de restauration du worker :
listing/extraction Borg et traitement des jobs de restauration.
"""
import json
from unittest.mock import MagicMock, patch

from api.database import Job, Snapshot
from worker.tasks import BorgManager, process_restore_job, enqueue_restore_job, enqueue_backup_job


def _reload(db_session, job_id):
    """Recharge un Job via une nouvelle requête (process_restore_job ferme la
    session à la fin, ce qui invalide un simple .refresh() sur l'instance)."""
    return db_session.query(Job).filter(Job.id == job_id).first()


# --- BorgManager.list_archive_contents ---

@patch('worker.tasks.subprocess.run')
def test_list_archive_contents_parses_json_lines(mock_run):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=(
            '{"path": "docs", "type": "d", "size": 0, "mtime": "2026-01-01T00:00:00"}\n'
            '{"path": "docs/a.txt", "type": "f", "size": 42, "mtime": "2026-01-01T00:00:00"}\n'
        ),
        stderr='',
    )

    borg = BorgManager('/tmp/repo', 'pass')
    result = borg.list_archive_contents('archive1')

    assert result['success'] is True
    assert len(result['entries']) == 2
    assert result['entries'][1] == {
        'path': 'docs/a.txt', 'type': 'f', 'size': 42, 'mtime': '2026-01-01T00:00:00'
    }


@patch('worker.tasks.subprocess.run')
def test_list_archive_contents_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=2, stdout='', stderr='repository does not exist')

    borg = BorgManager('/tmp/repo', 'pass')
    result = borg.list_archive_contents('archive1')

    assert result['success'] is False
    assert result['entries'] == []


# --- BorgManager.extract ---

@patch('worker.tasks.subprocess.run')
@patch('worker.tasks.os.makedirs')
def test_extract_builds_correct_command(mock_makedirs, mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

    borg = BorgManager('/tmp/repo', 'pass')
    result = borg.extract('archive1', '/tmp/out', paths=['docs/a.txt'])

    assert result['success'] is True
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd == ['borg', 'extract', '/tmp/repo::archive1', 'docs/a.txt']
    assert kwargs['cwd'] == '/tmp/out'


# --- process_restore_job ---

def _make_job_and_snapshot(db_session, agent, config):
    job = Job(agent_id=agent.id, type='restore', status='pending', config=json.dumps(config))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    snapshot = Snapshot(
        job_id=job.id, name='archive1', repo_path='/tmp/repo', size_bytes=100, is_full=True
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    return job, snapshot


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.shutil.make_archive')
@patch('worker.tasks.BorgManager.extract')
def test_process_restore_job_download_target_completes(
    mock_extract, mock_make_archive, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job, snapshot = _make_job_and_snapshot(
        db_session, agent,
        {'snapshot_id': None, 'selected_paths': ['docs/a.txt'], 'target': 'download'},
    )
    # snapshot_id n'est connu qu'après création du snapshot ci-dessus
    config = json.loads(job.config)
    config['snapshot_id'] = snapshot.id
    job.config = json.dumps(config)
    db_session.commit()
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_extract.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    mock_make_archive.return_value = '/tmp/restore_packages/1.zip'

    result = process_restore_job(job_id)

    assert result['success'] is True
    job = _reload(db_session, job_id)
    assert job.status == 'completed'
    assert job.finished_at is not None
    assert json.loads(job.config)['package_path'] == '/tmp/restore_packages/1.zip'


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.shutil.make_archive')
@patch('worker.tasks.BorgManager.extract')
def test_process_restore_job_agent_target_awaits_pickup(
    mock_extract, mock_make_archive, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job, snapshot = _make_job_and_snapshot(
        db_session, agent,
        {'snapshot_id': None, 'selected_paths': ['docs/a.txt'], 'target': 'agent', 'restore_path': '/home/user/restore'},
    )
    config = json.loads(job.config)
    config['snapshot_id'] = snapshot.id
    job.config = json.dumps(config)
    db_session.commit()
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_extract.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    mock_make_archive.return_value = '/tmp/restore_packages/2.zip'

    result = process_restore_job(job_id)

    assert result['success'] is True
    job = _reload(db_session, job_id)
    assert job.status == 'ready_for_agent'
    assert job.finished_at is None


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.extract')
def test_process_restore_job_extract_failure_marks_job_failed(
    mock_extract, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job, snapshot = _make_job_and_snapshot(
        db_session, agent,
        {'snapshot_id': None, 'selected_paths': ['docs/a.txt'], 'target': 'download'},
    )
    config = json.loads(job.config)
    config['snapshot_id'] = snapshot.id
    job.config = json.dumps(config)
    db_session.commit()
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_extract.return_value = {'success': False, 'stderr': 'archive corrompue'}

    result = process_restore_job(job_id)

    assert result['success'] is False
    job = _reload(db_session, job_id)
    assert job.status == 'failed'
    assert job.error_message == 'archive corrompue'


def test_process_restore_job_missing_snapshot_marks_job_failed(db_session, test_agent):
    agent, _ = test_agent
    job = Job(
        agent_id=agent.id, type='restore', status='pending',
        config=json.dumps({'snapshot_id': 9999, 'selected_paths': ['a.txt'], 'target': 'download'}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    job_id = job.id

    with patch('worker.tasks.SessionLocal', return_value=db_session):
        result = process_restore_job(job_id)

    assert result['success'] is False
    job = _reload(db_session, job_id)
    assert job.status == 'failed'


# --- enqueue_restore_job / enqueue_backup_job ---
#
# Régression : queue.enqueue() ne reconnaît que job_timeout= (pas timeout=)
# comme kwarg RQ ; un timeout= en trop est transmis tel quel à la fonction
# cible et fait planter le job avec TypeError dès son exécution (constaté
# en conditions réelles : un backup ou une restauration réels échouaient
# systématiquement avant même d'entrer dans process_backup_job/process_restore_job).

@patch('worker.tasks.queue')
def test_enqueue_restore_job_pushes_to_queue(mock_queue):
    mock_queue.enqueue.return_value = MagicMock(id='rq-job-42')

    rq_id = enqueue_restore_job(7)

    assert rq_id == 'rq-job-42'
    mock_queue.enqueue.assert_called_once()
    args, kwargs = mock_queue.enqueue.call_args
    assert args[1] == 7
    assert kwargs == {'job_timeout': '1h'}


@patch('worker.tasks.queue')
def test_enqueue_backup_job_pushes_to_queue(mock_queue):
    mock_queue.enqueue.return_value = MagicMock(id='rq-job-1')

    rq_id = enqueue_backup_job(3)

    assert rq_id == 'rq-job-1'
    mock_queue.enqueue.assert_called_once()
    args, kwargs = mock_queue.enqueue.call_args
    assert args[1] == 3
    assert kwargs == {'job_timeout': '1h'}
