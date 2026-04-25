import pytest
from datetime import datetime, timezone, timedelta
from job_scheduler.core.queue import JobQueue
from job_scheduler.types.job_types import Job, JobStatus

pytestmark = pytest.mark.asyncio


def make_job(job_type="test", data=None, scheduled_for=None, retry_count=0):
    return Job(
        job_type=job_type,
        data=data or {},
        scheduled_for=scheduled_for or datetime.now(timezone.utc),
        retry_count=retry_count,
    )


def past(seconds=10):
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def future(seconds=60):
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


# --- enqueue / len / is_empty ---

async def test_empty_on_init():
    q = JobQueue()
    assert len(q) == 0
    assert q.is_empty()


async def test_enqueue_increases_length():
    q = JobQueue()
    await q.enqueue(make_job())
    assert len(q) == 1
    assert not q.is_empty()


async def test_enqueue_multiple():
    q = JobQueue()
    await q.enqueue(make_job())
    await q.enqueue(make_job())
    assert len(q) == 2


# --- dequeue ---

async def test_dequeue_empty_returns_none():
    q = JobQueue()
    assert await q.dequeue() is None


async def test_dequeue_future_job_returns_none():
    q = JobQueue()
    await q.enqueue(make_job(scheduled_for=future()))
    assert await q.dequeue() is None


async def test_dequeue_returns_due_job():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    result = await q.dequeue()
    assert result is not None
    assert result.job_id == job.job_id


async def test_dequeue_returns_earliest_job():
    q = JobQueue()
    early = make_job(scheduled_for=past(seconds=20))
    late = make_job(scheduled_for=past(seconds=5))
    await q.enqueue(late)
    await q.enqueue(early)
    result = await q.dequeue()
    assert result.job_id == early.job_id


async def test_dequeue_sets_status_to_processing():
    q = JobQueue()
    await q.enqueue(make_job(scheduled_for=past()))
    result = await q.dequeue()
    assert result.status == JobStatus.PROCESSING


async def test_dequeue_removes_from_queue():
    q = JobQueue()
    await q.enqueue(make_job(scheduled_for=past()))
    await q.dequeue()
    assert len(q) == 0


async def test_dequeue_skips_future_returns_due():
    q = JobQueue()
    due = make_job(scheduled_for=past())
    await q.enqueue(make_job(scheduled_for=future()))
    await q.enqueue(due)
    result = await q.dequeue()
    assert result.job_id == due.job_id


# --- peek ---

async def test_peek_empty_returns_none():
    q = JobQueue()
    assert q.peek() is None


async def test_peek_returns_next_job_without_removing():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    peeked = q.peek()
    assert peeked.job_id == job.job_id
    assert len(q) == 1


# --- get ---

async def test_get_pending_job():
    q = JobQueue()
    job = make_job()
    await q.enqueue(job)
    assert q.get(job.job_id) is not None


async def test_get_inflight_job():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    await q.dequeue()
    assert q.get(job.job_id) is not None


async def test_get_unknown_returns_none():
    q = JobQueue()
    assert q.get("nonexistent-id") is None


# --- ack ---

async def test_ack_removes_from_inflight():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    await q.dequeue()
    await q.ack(job.job_id)
    assert q.get(job.job_id) is None


async def test_ack_sets_status_completed():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    dequeued = await q.dequeue()
    await q.ack(dequeued.job_id)
    # job removed from index — completed jobs are gone
    assert q.get(dequeued.job_id) is None


async def test_ack_unknown_job_raises():
    q = JobQueue()
    with pytest.raises(KeyError):
        await q.ack("nonexistent-id")


# --- nack ---

async def test_nack_requeues_job():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    await q.dequeue()
    await q.nack(job.job_id)
    assert len(q) == 1


async def test_nack_increments_retry_count():
    q = JobQueue()
    job = make_job(scheduled_for=past())
    await q.enqueue(job)
    await q.dequeue()
    await q.nack(job.job_id)
    requeued = q.get(job.job_id)
    assert requeued.retry_count == 1


async def test_nack_dead_letters_after_max_retries():
    q = JobQueue()
    job = make_job(scheduled_for=past(), retry_count=3)
    await q.enqueue(job)
    await q.dequeue()
    await q.nack(job.job_id)
    assert len(q) == 0
    assert q.get(job.job_id) is None
    assert any(j.job_id == job.job_id for j in q.dead_letter)


async def test_nack_unknown_job_raises():
    q = JobQueue()
    with pytest.raises(KeyError):
        await q.nack("nonexistent-id")


# --- dead letter ---

async def test_dead_letter_initially_empty():
    q = JobQueue()
    assert q.dead_letter == []


async def test_dead_lettered_job_has_failed_status():
    q = JobQueue()
    job = make_job(scheduled_for=past(), retry_count=3)
    await q.enqueue(job)
    await q.dequeue()
    await q.nack(job.job_id)
    assert q.dead_letter[0].status == JobStatus.FAILED
