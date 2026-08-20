"""
Tests pour l'instrumentation Prometheus événementielle du worker
(saveos_worker_jobs_total, saveos_worker_job_duration_seconds).

Le registre Prometheus est un singleton global au niveau du process :
les assertions comparent une valeur AVANT/APRÈS l'appel (delta), pour ne
pas dépendre de l'ordre d'exécution des autres tests.
"""
import json
from unittest.mock import patch

from prometheus_client import REGISTRY

from worker.tasks import process_backup_job, process_restore_job
from api.database import Job, Snapshot


def _counter_value(job_type, outcome):
    return REGISTRY.get_sample_value(
        'saveos_worker_jobs_total', {'job_type': job_type, 'outcome': outcome}
    ) or 0.0


def _histogram_count(job_type):
    return REGISTRY.get_sample_value('saveos_worker_job_duration_seconds_count', {'job_type': job_type}) or 0.0


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.BorgManager.init_repo')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_process_backup_job_success_records_metrics(
    mock_exists, mock_init, mock_create, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job = Job(agent_id=agent.id, type='backup', status='pending', config=json.dumps({'source_paths': ['/tmp/x']}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}

    before_count = _counter_value('backup', 'success')
    before_hist_count = _histogram_count('backup')

    result = process_backup_job(job_id)

    assert result['success'] is True
    assert _counter_value('backup', 'success') == before_count + 1
    assert _histogram_count('backup') == before_hist_count + 1


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_process_backup_job_failure_records_metrics(
    mock_exists, mock_create, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job = Job(agent_id=agent.id, type='backup', status='pending', config=json.dumps({'source_paths': ['/tmp/x']}))
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': False, 'stderr': 'boom'}

    before_count = _counter_value('backup', 'failure')

    result = process_backup_job(job_id)

    assert result['success'] is False
    assert _counter_value('backup', 'failure') == before_count + 1


def test_process_backup_job_missing_job_does_not_record_metrics(db_session):
    before_success = _counter_value('backup', 'success')
    before_failure = _counter_value('backup', 'failure')

    with patch('worker.tasks.SessionLocal', return_value=db_session):
        process_backup_job(999999)

    assert _counter_value('backup', 'success') == before_success
    assert _counter_value('backup', 'failure') == before_failure


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.shutil.make_archive')
@patch('worker.tasks.BorgManager.extract')
def test_process_restore_job_success_records_metrics(
    mock_extract, mock_make_archive, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    job = Job(agent_id=agent.id, type='restore', status='pending')
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    snapshot = Snapshot(job_id=job.id, name='archive1', repo_path='/tmp/repo', size_bytes=10, is_full=True)
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)

    job.config = json.dumps({'snapshot_id': snapshot.id, 'selected_paths': ['a.txt'], 'target': 'download'})
    db_session.commit()
    job_id = job.id

    mock_session_local.return_value = db_session
    mock_extract.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    mock_make_archive.return_value = '/tmp/restore_packages/x.zip'

    before_count = _counter_value('restore', 'success')

    result = process_restore_job(job_id)

    assert result['success'] is True
    assert _counter_value('restore', 'success') == before_count + 1


@patch('worker.tasks.SessionLocal')
def test_process_restore_job_missing_snapshot_records_failure_metric(mock_session_local, db_session, test_agent):
    agent, _ = test_agent
    job = Job(
        agent_id=agent.id, type='restore', status='pending',
        config=json.dumps({'snapshot_id': 999999, 'selected_paths': ['a.txt'], 'target': 'download'}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    mock_session_local.return_value = db_session

    before_count = _counter_value('restore', 'failure')

    result = process_restore_job(job.id)

    assert result['success'] is False
    assert _counter_value('restore', 'failure') == before_count + 1
