# Job Scheduler

A lightweight async job scheduler in Python.

## Overview

This project provides a simple in-memory job scheduling system with:

- scheduled job creation
- async queue operations
- due-job dequeuing
- ack/nack handling
- retry tracking
- dead-letter storage

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
pip install pydantic pytest pytest-asyncio
```

## Usage

```python
from datetime import timedelta

from job_scheduler.core.scheduler import Scheduler

scheduler = Scheduler()

job = await scheduler.schedule(
    job_type="email",
    data={"to": "user@example.com", "subject": "Welcome"},
)

later_job = await scheduler.schedule_in(
    delay=timedelta(minutes=30),
    job_type="report",
    data={"report_id": "monthly"},
)
```

## Project Structure

```text
job_scheduler/
  core/
    queue.py
    scheduler.py
  types/
    job_types.py
  workers/
    email_worker.py
    report_worker.py
tests/
  test_queue.py
  test_scheduler.py
docs/
```

## Running Tests

```bash
.venv/bin/pytest -q
```
