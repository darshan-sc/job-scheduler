from job_scheduler.types.job_types import Job, JobStatus
from heapq import heappush, heappop
import asyncio
from datetime import datetime, timezone
from typing import Final, List, Tuple

class JobQueue:
    MAX_RETRIES: Final[int] = 3 #can vary by job type

    def __init__(self):
        self._queue: List[Tuple[datetime, str,Job]] = [] #min-heap with jobs, ordered on schedule timing
        self._in_flight: dict[str, Job] = {}
        self._job_index: dict[str, Job] = {}
        self.dead_letter: List[Job] = []
        self._lock = asyncio.Lock()

        

    async def enqueue(self, job: Job) -> None:
        async with self._lock:
            heappush(self._queue, (job.scheduled_for, job.job_id, job))
            self._job_index[job.job_id] = job

    async def dequeue(self) -> Job | None:
        # returns None if empty or no jobs due yet
        async with self._lock:
            if not self._queue or self._queue[0][0] > datetime.now(timezone.utc):
                return None
            else: 
                _, _, job = heappop(self._queue)
                job.status = JobStatus.PROCESSING
                self._in_flight[job.job_id] = job
                return job

    async def ack(self, job_id: str) -> None:
        async with self._lock:
            job = self._in_flight[job_id]
            #job.job_type - implement logic for different jobs later
            job.status = JobStatus.COMPLETED
            del self._in_flight[job_id]
            del self._job_index[job_id]


    async def nack(self, job_id: str) -> None:
        async with self._lock:
            job = self._in_flight[job_id]
            #job.job_type - implement logic for different jobs later
            del self._in_flight[job_id]
            if job.retry_count + 1 > JobQueue.MAX_RETRIES:
                job.status = JobStatus.FAILED
                del self._job_index[job_id]
                self.dead_letter.append(job)
            else:
                job.retry_count += 1
                job.status = JobStatus.PENDING
                heappush(self._queue,(job.scheduled_for, job.job_id, job))

    def peek(self) -> Job | None:
        if not self._queue:
            return None
        else: 
            return self._queue[0][2]

    def get(self, job_id: str) -> Job | None:
        if job_id in self._job_index:
            return self._job_index[job_id]
        else:
            return None

    def __len__(self) -> int:
        return len(self._queue)

    def is_empty(self) -> bool:
        return len(self._queue) == 0
