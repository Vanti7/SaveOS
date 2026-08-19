"""
Endpoints de restauration granulaire : navigation dans le contenu d'une
archive Borg, création d'un job de restauration, téléchargement du paquet
résultant, et récupération/rapport côté agent.
"""
import json
import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.database import get_db, Agent, Job, Snapshot
from api.schemas import (
    RestoreTarget, RestoreJobCreate, ArchiveEntry, ArchiveBrowseRequest,
    ArchiveBrowseResponse, PendingRestoreJob, AgentReportRequest,
    JobResponse, JobStatus,
)
from api.auth import get_current_agent, get_current_principal, Principal
from worker.tasks import BorgManager, DEFAULT_BORG_PASSPHRASE, enqueue_restore_job

router = APIRouter()


def _get_owned_snapshot(db: Session, agent_id: int, snapshot_id: int) -> Snapshot:
    """Récupère un snapshot en vérifiant qu'il appartient bien à agent_id
    (jointure explicite : deux FK croisées jobs<->snapshots)."""
    snapshot = (
        db.query(Snapshot)
        .join(Job, Snapshot.job_id == Job.id)
        .filter(Snapshot.id == snapshot_id, Job.agent_id == agent_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot introuvable pour cet agent",
        )
    return snapshot


@router.post("/backup/{agent_id}/snapshots/{snapshot_id}/browse", response_model=ArchiveBrowseResponse)
async def browse_snapshot_contents(
    agent_id: int,
    snapshot_id: int,
    body: ArchiveBrowseRequest,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Liste le contenu d'une archive à un chemin donné (un niveau de
    dossier à la fois). Pas d'index persistant : reliste et filtre l'archive
    complète à chaque appel (acceptable à l'échelle MVP)."""

    if not principal.can_act_on_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut consulter que ses propres snapshots",
        )

    snapshot = _get_owned_snapshot(db, agent_id, snapshot_id)

    borg = BorgManager(snapshot.repo_path, body.passphrase or DEFAULT_BORG_PASSPHRASE)
    listing = borg.list_archive_contents(snapshot.name)
    if not listing['success']:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=listing.get('stderr') or listing.get('error') or "Erreur Borg",
        )

    prefix = body.path.strip('/')
    seen = set()
    entries: List[ArchiveEntry] = []
    for entry in listing['entries']:
        path = entry.get('path') or ''
        if prefix and not (path == prefix or path.startswith(prefix + '/')):
            continue
        remainder = path[len(prefix):].lstrip('/') if prefix else path
        if not remainder:
            continue
        first_segment = remainder.split('/', 1)[0]
        if first_segment in seen:
            continue
        seen.add(first_segment)
        is_direct_child = '/' not in remainder
        entries.append(ArchiveEntry(
            path=f"{prefix}/{first_segment}" if prefix else first_segment,
            type=entry.get('type') if is_direct_child else 'd',
            size=entry.get('size') if is_direct_child else None,
            mtime=entry.get('mtime') if is_direct_child else None,
        ))

    return ArchiveBrowseResponse(path=body.path, entries=entries)


@router.post("/restore", response_model=JobResponse)
async def create_restore_job(
    body: RestoreJobCreate,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Crée un job de restauration granulaire pour les chemins sélectionnés
    d'un snapshot."""

    if not principal.can_act_on_agent(body.agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut restaurer que pour lui-même",
        )

    if not body.selected_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_paths ne peut pas être vide",
        )

    if body.target == RestoreTarget.AGENT and not body.restore_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="restore_path est requis pour une restauration sur l'agent",
        )

    snapshot = _get_owned_snapshot(db, body.agent_id, body.snapshot_id)

    config = {
        'snapshot_id': snapshot.id,
        'selected_paths': body.selected_paths,
        'target': body.target.value,
        'restore_path': body.restore_path,
    }
    if body.passphrase:
        config['passphrase'] = body.passphrase

    new_job = Job(
        agent_id=body.agent_id,
        type='restore',
        status='pending',
        snapshot_id=snapshot.id,
        config=json.dumps(config),
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    try:
        enqueue_restore_job(new_job.id)
    except Exception as e:
        new_job.status = 'failed'
        new_job.error_message = f"Erreur lors de l'ajout à la queue: {str(e)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du job de restauration",
        )

    return new_job


@router.get("/restore/{job_id}/download")
async def download_restore_package(
    job_id: int,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Sert le paquet zip résultant d'une restauration. Consommé aussi bien
    par le tableau de bord (déclenche un téléchargement navigateur) que par
    l'agent lui-même (récupère le paquet avant extraction locale)."""

    job = db.query(Job).filter(Job.id == job_id, Job.type == 'restore').first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job de restauration introuvable")

    if not principal.can_act_on_agent(job.agent_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut télécharger que ses propres restaurations",
        )

    if job.status not in (JobStatus.COMPLETED.value, JobStatus.READY_FOR_AGENT.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paquet non prêt (statut actuel: {job.status})",
        )

    config = json.loads(job.config) if job.config else {}
    package_path = config.get('package_path')
    if not package_path or not os.path.exists(package_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paquet de restauration introuvable")

    return FileResponse(package_path, media_type='application/zip', filename=f"restore_{job_id}.zip")


@router.get("/agents/me/pending-restores", response_model=List[PendingRestoreJob])
async def list_pending_restores(
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Jobs de restauration prêts à être récupérés par l'agent courant."""

    jobs = db.query(Job).filter(
        Job.agent_id == current_agent.id,
        Job.type == 'restore',
        Job.status == JobStatus.READY_FOR_AGENT.value,
    ).order_by(Job.created_at.asc()).all()

    return [
        PendingRestoreJob(
            id=j.id,
            snapshot_id=j.snapshot_id,
            config=json.loads(j.config) if j.config else {},
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.post("/jobs/{job_id}/agent-report", response_model=JobResponse)
async def report_restore_status(
    job_id: int,
    body: AgentReportRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """L'agent rapporte le résultat (completed/failed) d'une restauration
    qu'il vient d'appliquer localement."""

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job introuvable")

    if job.agent_id != current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un agent ne peut rapporter que ses propres jobs",
        )

    if job.status != JobStatus.READY_FOR_AGENT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job non éligible au rapport (statut actuel: {job.status})",
        )

    if body.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status doit être 'completed' ou 'failed'",
        )

    job.status = body.status.value
    job.finished_at = datetime.utcnow()
    if body.status == JobStatus.FAILED:
        job.error_message = body.error_message

    db.commit()
    db.refresh(job)
    return job
