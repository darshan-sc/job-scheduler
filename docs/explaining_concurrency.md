# Explaining Concurrency

## Why Threads Exist Here

The `JobQueue` itself doesn't spawn threads — but it's designed to sit in the middle of an application that has several. Here's the full picture for a typical job scheduler like this one:

## The Threads in Play

**1. Worker threads (the main reason)**

You don't want jobs processed one-at-a-time. If you have 100 emails to send and each takes 500ms, serial processing takes 50s; 10 parallel workers finish in ~5s. So the app spawns N worker threads, each running a loop like:

```python
while True:
    job = queue.dequeue()
    if job:
        process(job)
        queue.ack(job.id)
```

All N threads hammer the same `JobQueue` instance simultaneously. That's the core concurrency source.

**2. A producer/scheduler thread**

Something has to call `enqueue()` — an API handler, a cron-like scheduler that wakes up and pushes due jobs, a Kafka consumer, etc. That runs on a different thread than the workers, so `enqueue` races with `dequeue`.

**3. A reaper/watchdog thread** (mentioned in `concurrency.md`)

Periodically scans `in_flight` for jobs stuck too long (worker crashed) and requeues them. Another independent thread mutating the same state.

**4. The HTTP/API thread pool**

If there's a status endpoint like `GET /jobs/:id`, the web framework (FastAPI, Flask) serves each request on its own thread, each calling `queue.get(job_id)` — concurrent reads racing with worker writes.

## What Goes Wrong Without a Lock

The shared state is a **heap list**, an **in-flight dict**, and a **job index dict**. None of these are atomic at the Python level. A `heappush` is multiple bytecode operations — swap, sift-up, reassign. If thread A is mid-sift and thread B does a `heappop`, the heap invariant breaks and you get silent corruption.

The classic failure is two workers both calling `dequeue()`, both reading the same top-of-heap entry before either pops it — same job processed twice. Email sent twice. Payment charged twice.

## Why the GIL Doesn't Save You

A common misconception: "Python has the GIL, so threads can't really run in parallel — do I need locks?" Yes. The GIL guarantees one bytecode at a time, not one *method call* at a time. `heappush` is ~dozens of bytecodes; the GIL can switch threads in the middle. You still need `threading.Lock` to make multi-step operations atomic.

## The Async Alternative

If workers are I/O-bound (calling APIs, sending email), `asyncio` with one thread and cooperative task-switching is lighter. You still need `asyncio.Lock` because `await` points are yield points where another task can interleave — same class of race conditions, different mechanism.

## TL;DR

Threads aren't accidental — the whole point of a job queue is fan-out: one producer, many consumers, running concurrently. The lock exists because `heap`, `in_flight`, and `job_index` are shared mutable state touched by all those threads, and Python-level operations on them aren't atomic.
