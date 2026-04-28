from typing import TypeVar
from datetime import datetime, timedelta, timezone

from job_scheduler.core.queue import JobQueue
from job_scheduler.types.job_types import Job

T = TypeVar('T')

class Scheduler:
    def __init__(self, queue: JobQueue | None = None):
        self.queue = queue or JobQueue()
    

    async def schedule(self, job_type: str, data: T, scheduled_for: datetime | None = None)->Job:
        job = Job(job_type=job_type, data=data)
        if scheduled_for is not None:
            job.scheduled_for = scheduled_for
        
        await self.queue.enqueue(job)
        return job


    async def schedule_in(self, delay: timedelta, job_type: str, data: T) -> Job:
        if delay < timedelta(0):
            raise ValueError("delay cannot be negative!")

        return await self.schedule(job_type, data, datetime.now(timezone.utc) + delay)
        

    def get_job(self, job_id: str) -> Job | None:
        return self.queue.get(job_id)
