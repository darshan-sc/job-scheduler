# Concurrency in the Job Queue

## The Problem

Multiple workers pull from the same queue simultaneously. Without coordination, two workers can dequeue the same job, a crashed worker can silently drop a job, or a job's state can be corrupted mid-update.

---

## Core Mechanism: `threading.Lock`

All mutations to the queue's internal state (the heap, the in-flight dict, the job index) are guarded by a single `Lock`. Only one thread can hold it at a time.

```
Worker A: dequeue() ──► acquire lock ──► pop heap ──► release lock
Worker B: dequeue() ──────────────────► blocked ──► acquire lock ──► pop heap ──► release lock
```

This makes `enqueue`, `dequeue`, `ack`, and `nack` **atomic** — no partial reads or writes.

---

## In-Flight Tracking

When a job is dequeued, it is not deleted — it moves to an **in-flight dict** keyed by `job_id`. It stays there until the worker explicitly calls `ack` or `nack`.

```
[heap]  ──dequeue()──►  [in_flight]  ──ack()──►  (removed)
                                      ──nack()──►  [heap]  (requeued)
```

**Why**: if a worker crashes after dequeuing but before finishing, the job is not lost — it remains in `in_flight`. A watchdog/reaper thread can periodically scan `in_flight` for jobs that have been there too long and requeue them.

---

## Race Conditions Prevented

| Scenario | Without locking | With lock + in-flight |
|---|---|---|
| Two workers dequeue same job | Both process it (duplicate work) | Only one gets it |
| Worker crashes mid-job | Job is lost | Job stays in `in_flight`, reaper requeues it |
| Enqueue during dequeue | Heap corruption | Blocked until dequeue finishes |
| `nack` while another thread enqueues | Inconsistent heap state | Serialized via lock |

---

## Visibility: The Job Index

Alongside the heap and in-flight dict, a `job_index: dict[str, Job]` provides O(1) lookup by `job_id`. It holds references to all known jobs regardless of state.

```
job_index = {
    "abc": Job(status=PENDING),    # in heap
    "def": Job(status=PROCESSING), # in in_flight
}
```

This is also lock-guarded. It's what `get(job_id)` reads from.

---

## Retry and Dead Letter

`nack` increments `retry_count` before requeueing. Once `retry_count` exceeds a threshold (e.g. 3), the job is moved to a **dead letter queue** (a separate list) instead of being requeued. This prevents a bad job from looping forever and starving the queue.

```
nack():
    job.retry_count += 1
    if job.retry_count > MAX_RETRIES:
        dead_letter.append(job)
    else:
        heappush(heap, job)
```

---

## Async Alternative

If the workers are I/O-bound (e.g. sending emails, hitting APIs), `asyncio` with `asyncio.Lock` is a better fit than threads — lower overhead, no GIL contention. The API stays identical; only the lock type and `async/await` keywords change. Decide based on whether your workers do I/O or CPU work.

---

## Summary

| Component | Purpose |
|---|---|
| `threading.Lock` | Serializes all state mutations |
| In-flight dict | Prevents job loss on worker crash |
| Job index | O(1) lookup by `job_id` |
| Retry count + dead letter | Prevents infinite retry loops |
| Reaper thread (future) | Recovers stalled in-flight jobs |
