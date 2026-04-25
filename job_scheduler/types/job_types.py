from enum import StrEnum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import TypeVar, Generic
from uuid import uuid4

class JobStatus(StrEnum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

T = TypeVar('T')

class Job(BaseModel, Generic[T]):
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    job_type: str
    data: T
    status: JobStatus = JobStatus.PENDING
    scheduled_for: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
