"""Bounded execution with durable acceptance and renewable ownership."""
import asyncio
import logging
import uuid

from database import jobs

logger = logging.getLogger('footy.jobs')
_tasks = set()


async def execute_job(job_id, processor, broadcast):
    owner = uuid.uuid4().hex
    job = jobs.claim_job(job_id, owner)
    if job is None:
        return

    async def keep_lease():
        while True:
            await asyncio.sleep(10)
            if not jobs.heartbeat(job_id, owner):
                return

    lease = asyncio.create_task(keep_lease())
    loop = asyncio.get_running_loop()

    def emit(event):
        future = asyncio.run_coroutine_threadsafe(
            broadcast(event.event, data=event.model_dump(exclude={'event'})), loop)
        try:
            future.result(timeout=5)
        except TimeoutError:
            logger.warning('Event delivery timed out for job %s', job_id)

    job['emit'] = emit
    try:
        if job['kind'] == 'simulation':
            await broadcast('SIMULATION_START', message='Simulation started',
                            data={'job_id': job_id, 'run_id': job['run_id']})
        if job['kind'] == 'evaluation':
            # Evaluation seeds Python/NumPy/Torch. A separate process prevents
            # those seeds from changing a concurrently running campaign's RNG.
            from concurrent.futures import ProcessPoolExecutor
            import multiprocessing
            executor = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn'))
            try:
                serializable_job = {key: value for key, value in job.items() if key != 'emit'}
                result = await loop.run_in_executor(executor, processor, serializable_job)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            result = await asyncio.to_thread(processor, job)
        jobs.finish_job(job_id, owner, 'completed', result=result)
        final = jobs.get_job(job_id)
        event = 'ML_EVAL_COMPLETE' if job['kind'] == 'evaluation' else 'SIMULATION_COMPLETE'
        await broadcast(event if final['status'] == 'completed' else 'JOB_CANCELLED',
                        message=f"Job {final['status']}",
                        data={'job_id': job_id, 'run_id': job['run_id'], 'result': result})
    except jobs.JobCancelled as exc:
        jobs.finish_job(job_id, owner, 'cancelled', error=str(exc))
    except asyncio.CancelledError:
        # Thread execution may still be winding down; retain the lease until expiry.
        # New processes reconcile it, rather than immediately overlapping work.
        jobs.cancel_job(job_id)
        raise
    except Exception as exc:
        logger.exception('Job %s failed', job_id)
        jobs.finish_job(job_id, owner, 'failed', error=str(exc))
        await broadcast('JOB_ERROR', message='Job failed', data={'job_id': job_id, 'run_id': job['run_id']})
    finally:
        lease.cancel()
        await asyncio.gather(lease, return_exceptions=True)


def schedule(job_id, processor, broadcast):
    task = asyncio.create_task(execute_job(job_id, processor, broadcast))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task


async def dispatch_pending(processors, broadcast):
    while True:
        jobs.reconcile_expired()
        for job_id in jobs.queued_jobs():
            job = jobs.get_job(job_id)
            schedule(job_id, processors[job['kind']], broadcast)
        await asyncio.sleep(5)


async def shutdown():
    pending = list(_tasks)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
