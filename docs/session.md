# Session Context

## What We've Done

### `job_scheduler/types/job_types.py`
- Migrated from `@dataclass` to `pydantic.BaseModel` for serialization + validation
- Switched `JobStatus(str, Enum)` to `JobStatus(StrEnum)` (available in 3.11+)
- Using `TypeVar` + `Generic[T]` pattern (on Python 3.11.9, so no 3.12 syntax)

Current state:
```python
from enum import StrEnum
from pydantic import StrEnum  # linter rewrote import here — worth double checking
from datetime import datetime
from typing import TypeVar, Generic

class JobStatus(StrEnum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

T = TypeVar('T')

class Job(BaseModel, Generic[T]):
    id: str
    type: str
    data: T
    status: JobStatus
    scheduled_for: datetime
    retry_count: int
```

> **Note**: We discussed making `id`, `type`, `status`, `scheduled_for`, `retry_count` more pythonic (rename builtins, add defaults) but **did not apply it yet**. Suggested version:
> ```python
> class Job(BaseModel, Generic[T]):
>     job_id: str = Field(default_factory=lambda: str(uuid4()))
>     job_type: str
>     data: T
>     status: JobStatus = JobStatus.PENDING
>     scheduled_for: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
>     retry_count: int = 0
> ```

---

### `job_scheduler/core/queue.py`
- Currently a stub (`class JobQueue: pass`)
- **Next task**: implement this class, using TDD (write tests first)

#### Agreed Design Decisions
- **Ordering**: min-heap on `scheduled_for` (O(log n) enqueue/dequeue)
- **Thread safety**: `threading.Lock` guarding all mutations
- **In-flight tracking**: jobs move to an in-flight dict on dequeue, removed on `ack`/`nack`
- **`dequeue`**: only returns jobs where `scheduled_for <= now`

#### Open Questions (answer before writing tests)
1. Should `nack` have a max retry limit → dead letter queue? (Recommended: yes, e.g. 3 retries)
2. Sync (`threading`) or async (`asyncio`)? Depends on whether workers are I/O or CPU bound.

#### Planned API
```python
class JobQueue:
    def enqueue(self, job: Job) -> None
    def dequeue(self) -> Job | None        # returns None if empty or no jobs due yet
    def peek(self) -> Job | None
    def ack(self, job_id: str) -> None
    def nack(self, job_id: str) -> None    # requeues or dead-letters based on retry_count
    def get(self, job_id: str) -> Job | None
    def __len__(self) -> int
    def is_empty(self) -> bool
```

---

## Environment
- Python 3.11.9
- Venv at `.venv/`
- Pydantic 2.12.5 installed
- No `requirements.txt` or `pyproject.toml` yet

## File Map
```
job_scheduler/
  types/job_types.py     # Job model + JobStatus — done (minor cleanup pending)
  core/queue.py          # JobQueue stub — next to implement
  core/scheduler.py      # empty
  workers/email_worker.py  # empty
  workers/report_worker.py # empty
docs/
  concurrency.md         # concurrency design doc
  session.md             # this file
```

## Next Steps
1. Decide open questions above
2. Write tests for `JobQueue` (TDD)
3. Implement `JobQueue`
4. Apply pythonic cleanup to `Job` model (defaults, rename builtins)
