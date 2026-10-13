"""SQLite-backed job acceptance, exclusive ownership and restart reconciliation."""
import json
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from database.models import SimulationRun, WorkJob
from database.session import get_db_session

LEASE_SECONDS = 60
TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted'}


class JobBusyError(Exception):
    pass


class JobCancelled(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def job_dict(job):
    return {'job_id': job.job_id, 'kind': job.kind, 'run_id': job.run_id,
            'status': job.status, 'created_at': job.created_at,
            'started_at': job.started_at, 'finished_at': job.finished_at,
            'cancel_requested': job.cancel_requested, 'error_message': job.error_message,
            'result': json.loads(job.result_json) if job.result_json else None,
            'payload': json.loads(job.payload_json)}


def submit_job(kind, payload, request_key=None):
    from database.admin_lock import administration_lock
    with administration_lock():
        return _submit_job(kind, payload, request_key)


def _submit_job(kind, payload, request_key=None):
    """Create the run and acceptance resource in the same committed transaction."""
    if request_key and len(request_key) > 128:
        raise ValueError('Idempotency key must be at most 128 characters')
    reconcile_expired()
    with get_db_session() as db:
        if request_key:
            previous = db.scalar(select(WorkJob).where(WorkJob.kind == kind, WorkJob.request_key == request_key))
            if previous:
                if json.loads(previous.payload_json) != payload:
                    raise ValueError('Idempotency key was already used with different parameters')
                return job_dict(previous)
        identity = uuid.uuid4().hex
        run_id = f'run_{identity}' if kind == 'simulation' else None
        if run_id:
            db.add(SimulationRun(run_id=run_id, season_year=payload['season_year'],
                                 created_at=now(), status='queued', render_mode=payload['render_mode'],
                                 total_matches=payload.get('total_matches', 380), matches_played=0))
            db.flush()
        job = WorkJob(job_id=identity, kind=kind, active_key=kind,
                      request_key=request_key, run_id=run_id, status='queued',
                      created_at=now(), payload_json=json.dumps(payload, sort_keys=True))
        db.add(job)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if request_key:
                previous = db.scalar(select(WorkJob).where(WorkJob.kind == kind, WorkJob.request_key == request_key))
                if previous and json.loads(previous.payload_json) == payload:
                    return job_dict(previous)
            raise JobBusyError(f'A {kind} job is already active') from exc
        return job_dict(job)


def get_job(job_id):
    with get_db_session() as db:
        job = db.get(WorkJob, job_id)
        if job is None:
            raise KeyError(job_id)
        return job_dict(job)


def queued_jobs():
    with get_db_session() as db:
        return list(db.scalars(select(WorkJob.job_id).where(WorkJob.status == 'queued')))


def claim_job(job_id, owner):
    with get_db_session() as db:
        claimed = db.execute(update(WorkJob).where(WorkJob.job_id == job_id, WorkJob.status == 'queued',
                                                  WorkJob.cancel_requested.is_(False)).values(
            status='running', started_at=now(), lease_owner=owner, lease_until=time.time() + LEASE_SECONDS))
        if not claimed.rowcount:
            return None
        job = db.get(WorkJob, job_id)
        if job.run_id:
            run = db.get(SimulationRun, job.run_id)
            run.status, run.started_at, run.heartbeat_at = 'running', now(), now()
        return job_dict(job)


def heartbeat(job_id, owner):
    with get_db_session() as db:
        changed = db.execute(update(WorkJob).where(WorkJob.job_id == job_id, WorkJob.lease_owner == owner,
                                                  WorkJob.status == 'running').values(
            lease_until=time.time() + LEASE_SECONDS))
        return bool(changed.rowcount)


def finish_job(job_id, owner, status, result=None, error=None):
    if status not in TERMINAL:
        raise ValueError('Invalid terminal job state')
    with get_db_session() as db:
        job = db.get(WorkJob, job_id)
        if job is None or job.lease_owner != owner or job.status in TERMINAL:
            return False
        job.status = 'cancelled' if job.cancel_requested else status
        job.active_key, job.finished_at, job.lease_until = None, now(), None
        job.result_json = json.dumps(result) if result is not None else None
        job.error_message = error
        if job.run_id:
            run = db.get(SimulationRun, job.run_id)
            run.status, run.finished_at, run.error_message = job.status, job.finished_at, error
        return True


def cancel_job(job_id):
    with get_db_session() as db:
        job = db.get(WorkJob, job_id)
        if job is None:
            raise KeyError(job_id)
        if job.status not in TERMINAL:
            job.cancel_requested = True
            if job.status == 'queued':
                job.status, job.finished_at, job.active_key = 'cancelled', now(), None
            if job.run_id:
                run = db.get(SimulationRun, job.run_id)
                run.cancel_requested = True
                if job.status == 'cancelled':
                    run.status, run.finished_at = 'cancelled', job.finished_at
        return job_dict(job)


def check_cancelled(job_id):
    if get_job(job_id)['cancel_requested']:
        raise JobCancelled('Job cancelled')


def reconcile_expired():
    """Never restart a partially committed season automatically."""
    with get_db_session() as db:
        expired = db.scalars(select(WorkJob).where(WorkJob.status == 'running', WorkJob.lease_until < time.time())).all()
        for job in expired:
            job.status, job.active_key, job.finished_at = 'interrupted', None, now()
            job.cancel_requested = True
            job.error_message = 'Worker lease expired; partial results were preserved'
            if job.run_id:
                run = db.get(SimulationRun, job.run_id)
                run.status, run.finished_at, run.error_message = job.status, job.finished_at, job.error_message
                run.cancel_requested = True
        return len(expired)


def has_active_jobs():
    reconcile_expired()
    with get_db_session() as db:
        return db.scalar(select(WorkJob.job_id).where(WorkJob.active_key.is_not(None)).limit(1)) is not None


def invalidate_restored_jobs():
    """Snapshot restoration preserves results, not a former worker's ownership."""
    with get_db_session() as db:
        for job in db.scalars(select(WorkJob).where(WorkJob.status.in_(['queued', 'running']))).all():
            job.status, job.active_key, job.finished_at = 'interrupted', None, now()
            job.cancel_requested = True
            job.error_message = 'Database snapshot restored; previous worker ownership is invalid'
            if job.run_id:
                run = db.get(SimulationRun, job.run_id)
                run.status, run.cancel_requested, run.error_message = job.status, True, job.error_message
