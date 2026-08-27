"""
Tests pour la purge automatique des anciens snapshots selon la politique de
rétention du tenant (worker/tasks.py::BorgManager.prune,
_reconcile_pruned_snapshots, hook dans process_backup_job) — voir
docs/adr/0006-facturation-quotas.md.
"""
import json
from unittest.mock import patch, MagicMock

from worker.tasks import BorgManager, process_backup_job
from api.database import Job, Snapshot, Tenant


def _make_job(db_session, agent, config=None):
    job = Job(
        agent_id=agent.id, type='backup', status='pending',
        config=json.dumps(config or {'source_paths': ['/tmp/x']}),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# --- BorgManager.prune : construction de la commande ---

@patch('worker.tasks.subprocess.run')
def test_prune_builds_command_from_recognized_retention_keys(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
    borg = BorgManager('/tmp/repo', 'pass')

    result = borg.prune({'daily': 7, 'weekly': 4, 'monthly': 6})

    assert result['success'] is True
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert cmd[:3] == ['borg', 'prune', '--list']
    assert '--keep-daily' in cmd and cmd[cmd.index('--keep-daily') + 1] == '7'
    assert '--keep-weekly' in cmd and cmd[cmd.index('--keep-weekly') + 1] == '4'
    assert '--keep-monthly' in cmd and cmd[cmd.index('--keep-monthly') + 1] == '6'
    assert cmd[-1] == '/tmp/repo'


@patch('worker.tasks.subprocess.run')
def test_prune_only_includes_provided_keys(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
    borg = BorgManager('/tmp/repo', 'pass')

    borg.prune({'daily': 7})

    cmd = mock_run.call_args[0][0]
    assert '--keep-daily' in cmd
    assert '--keep-weekly' not in cmd
    assert '--keep-monthly' not in cmd


# --- process_backup_job : déclenchement de la purge ---

@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.list_archives')
@patch('worker.tasks.BorgManager.prune')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_backup_success_triggers_prune_with_tenant_retention_policy(
    mock_exists, mock_create, mock_prune, mock_list, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    tenant = db_session.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
    tenant.retention_policy = json.dumps({'daily': 30, 'weekly': 12, 'monthly': 12})
    db_session.commit()

    job = _make_job(db_session, agent)
    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}
    mock_prune.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    mock_list.return_value = {'success': True, 'archives': []}

    result = process_backup_job(job.id)

    assert result['success'] is True
    mock_prune.assert_called_once_with({'daily': 30, 'weekly': 12, 'monthly': 12})


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.prune')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_backup_success_skips_prune_when_retention_policy_empty(
    mock_exists, mock_create, mock_prune, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    tenant = db_session.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
    tenant.retention_policy = json.dumps({})
    db_session.commit()

    job = _make_job(db_session, agent)
    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}

    result = process_backup_job(job.id)

    assert result['success'] is True
    mock_prune.assert_not_called()


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.prune')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_backup_success_skips_prune_when_retention_policy_missing(
    mock_exists, mock_create, mock_prune, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    tenant = db_session.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
    tenant.retention_policy = None
    db_session.commit()

    job = _make_job(db_session, agent)
    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}

    result = process_backup_job(job.id)

    assert result['success'] is True
    mock_prune.assert_not_called()


# --- Réconciliation DB après purge ---

@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.list_archives')
@patch('worker.tasks.BorgManager.prune')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_pruned_snapshots_removed_and_referencing_job_nulled(
    mock_exists, mock_create, mock_prune, mock_list, mock_session_local, db_session, test_agent
):
    agent, _ = test_agent
    tenant = db_session.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
    tenant.retention_policy = json.dumps({'daily': 7})
    db_session.commit()

    repo_path = f'/tmp/borg_repos/{agent.hostname}'
    old_job = _make_job(db_session, agent)
    old_snapshot = Snapshot(job_id=old_job.id, name='old-archive', repo_path=repo_path, size_bytes=100)
    db_session.add(old_snapshot)
    db_session.commit()
    db_session.refresh(old_snapshot)
    old_job.snapshot_id = old_snapshot.id
    db_session.commit()
    old_snapshot_id = old_snapshot.id
    old_job_id = old_job.id

    new_job = _make_job(db_session, agent)
    mock_session_local.return_value = db_session
    mock_create.return_value = {
        'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}
    }
    mock_prune.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    # L'ancienne archive a été purgée : seule la nouvelle reste.
    new_archive_name = None

    def fake_create_backup(source_paths, archive_name):
        nonlocal new_archive_name
        new_archive_name = archive_name
        return {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}

    mock_create.side_effect = fake_create_backup
    mock_list.side_effect = lambda: {'success': True, 'archives': [{'name': new_archive_name}]}

    result = process_backup_job(new_job.id)

    assert result['success'] is True
    assert db_session.query(Snapshot).filter(Snapshot.id == old_snapshot_id).first() is None
    refreshed_job = db_session.query(Job).filter(Job.id == old_job_id).first()
    assert refreshed_job.snapshot_id is None


@patch('worker.tasks.SessionLocal')
@patch('worker.tasks.BorgManager.list_archives')
@patch('worker.tasks.BorgManager.prune')
@patch('worker.tasks.BorgManager.create_backup')
@patch('worker.tasks.os.path.exists', return_value=True)
def test_reconciliation_skipped_when_archive_list_empty(
    mock_exists, mock_create, mock_prune, mock_list, mock_session_local, db_session, test_agent
):
    """Garde-fou : une liste d'archives vide (anomalie potentielle) ne doit
    jamais entraîner une suppression en masse des snapshots existants."""
    agent, _ = test_agent
    tenant = db_session.query(Tenant).filter(Tenant.id == agent.tenant_id).first()
    tenant.retention_policy = json.dumps({'daily': 7})
    db_session.commit()

    repo_path = f'/tmp/borg_repos/{agent.hostname}'
    existing_job = _make_job(db_session, agent)
    existing_snapshot = Snapshot(job_id=existing_job.id, name='existing', repo_path=repo_path, size_bytes=100)
    db_session.add(existing_snapshot)
    db_session.commit()
    existing_snapshot_id = existing_snapshot.id

    new_job = _make_job(db_session, agent)
    mock_session_local.return_value = db_session
    mock_create.return_value = {'success': True, 'stdout': '', 'stderr': '', 'stats': {'compressed_size': 10}}
    mock_prune.return_value = {'success': True, 'stdout': '', 'stderr': ''}
    mock_list.return_value = {'success': True, 'archives': []}

    result = process_backup_job(new_job.id)

    assert result['success'] is True
    assert db_session.query(Snapshot).filter(Snapshot.id == existing_snapshot_id).first() is not None
