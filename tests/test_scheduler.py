from datetime import datetime, timedelta, timezone

import pytest

from job_scheduler.core.scheduler import Scheduler
from job_scheduler.types.job_types import Job, JobStatus

pytestmark = pytest.mark.asyncio


class RecordingQueue:
    def __init__(self):
        self.enqueued = []
        self.jobs_by_id = {}

    async def enqueue(self, job: Job) -> None:
        self.enqueued.append(job)
        self.jobs_by_id[job.job_id] = job

    def get(self, job_id: str) -> Job | None:
        return self.jobs_by_id.get(job_id)


async def test_schedule_creates_pending_job_and_enqueues_it():
    queue = RecordingQueue()
    scheduler = Scheduler(queue=queue)

    job = await scheduler.schedule(
        job_type="email",
        data={"to": "user@example.com", "subject": "Welcome"},
    )

    assert isinstance(job, Job)
    assert job.job_type == "email"
    assert job.data == {"to": "user@example.com", "subject": "Welcome"}
    assert job.status == JobStatus.PENDING
    assert job.retry_count == 0
    assert queue.enqueued == [job]


async def test_schedule_defaults_scheduled_for_to_current_utc_time():
    queue = RecordingQueue()
    scheduler = Scheduler(queue=queue)
    before = datetime.now(timezone.utc)

    job = await scheduler.schedule(job_type="report", data={"report_id": "daily"})

    after = datetime.now(timezone.utc)
    assert before <= job.scheduled_for <= after
    assert job.scheduled_for.tzinfo == timezone.utc


async def test_schedule_preserves_explicit_scheduled_for_time():
    queue = RecordingQueue()
    scheduler = Scheduler(queue=queue)
    scheduled_for = datetime.now(timezone.utc) + timedelta(hours=2)

    job = await scheduler.schedule(
        job_type="email",
        data={"to": "later@example.com"},
        scheduled_for=scheduled_for,
    )

    assert job.scheduled_for == scheduled_for
    assert queue.enqueued == [job]


async def test_schedule_in_schedules_relative_to_now():
    queue = RecordingQueue()
    scheduler = Scheduler(queue=queue)
    delay = timedelta(minutes=30)
    before = datetime.now(timezone.utc) + delay

    job = await scheduler.schedule_in(
        delay=delay,
        job_type="report",
        data={"report_id": "monthly"},
    )

    after = datetime.now(timezone.utc) + delay
    assert before <= job.scheduled_for <= after
    assert queue.enqueued == [job]


async def test_schedule_rejects_negative_delay():
    scheduler = Scheduler(queue=RecordingQueue())

    with pytest.raises(ValueError, match="delay"):
        await scheduler.schedule_in(
            delay=timedelta(seconds=-1),
            job_type="email",
            data={},
        )


async def test_get_job_delegates_to_queue_index():
    queue = RecordingQueue()
    scheduler = Scheduler(queue=queue)
    job = await scheduler.schedule(job_type="email", data={"to": "user@example.com"})

    assert scheduler.get_job(job.job_id) is job
    assert scheduler.get_job("missing-job-id") is None
