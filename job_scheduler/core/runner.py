import asyncio
import logging
from job_scheduler.core.queue import JobQueue
from job_scheduler.types.job_types import Job
from typing import Callable

logger = logging.getLogger(__name__)

class WorkerRunner:
    def __init__(self, queue: JobQueue, workers: dict[str, Callable]):
        self.queue = queue
        self.workers = workers
    
    async def run_once(self) -> Job | None:
        job = await self.queue.dequeue()
        if job is None:
            return None

        try:
            worker = self.workers[job.job_type]
            await worker(job.data)
        except Exception:
            await self.queue.nack(job.job_id)
            raise 
        
        await self.queue.ack(job.job_id)
        return job
    
    async def run_forever(self, poll_interval: float = 1.0) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Worker run failed: %s", exc)
            await asyncio.sleep(poll_interval)
