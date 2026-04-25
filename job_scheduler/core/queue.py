from job_scheduler.types.job_types import Job, JobStatus

class JobQueue:
    def enqueue(self, job: Job) -> None:
        pass
    def dequeue(self) -> Job | None:
        pass        # returns None if empty or no jobs due yet
    def peek(self) -> Job | None:
        pass
    def ack(self, job_id: str) -> None:
        pass
    def nack(self, job_id: str) -> None:
        pass    # requeues or dead-letters based on retry_count
    def get(self, job_id: str) -> Job | None:
        pass
    def __len__(self) -> int:
        pass
    def is_empty(self) -> bool:
        pass
