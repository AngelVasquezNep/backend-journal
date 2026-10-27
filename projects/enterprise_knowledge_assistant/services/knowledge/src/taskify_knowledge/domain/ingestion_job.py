"""Durable ingestion attempts carry lease fences and allow at most three transient retries."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from taskify_knowledge.domain.constraints import ids, utc
from taskify_knowledge.domain.values import sequence

MAX_INGESTION_ATTEMPTS = (
    4  # Initial attempt plus the three retries permitted by the internal contract.
)


@dataclass(frozen=True, kw_only=True)
class IngestionJob:
    """Keep one logical job/revision/pipeline; stale lease holders cannot publish.

    Claims occur outside long transactions; retry only transient failures, at most three times.
    """

    id: UUID
    company_id: UUID
    revision_id: UUID
    pipeline_version: str
    state: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    attempt_count: int
    run_after: datetime
    lease_owner: UUID | None = None
    lease_until: datetime | None = None
    lease_version: int = 0
    heartbeat_at: datetime | None = None
    last_error_code: str | None = None
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate owned queue data before processing, including recovered lease metadata."""
        ids(self.id, self.company_id, self.revision_id)
        if self.lease_owner is not None:
            ids(self.lease_owner)
        sequence(self.lease_version)
        if (
            type(self.attempt_count) is not int
            or not 0 <= self.attempt_count <= MAX_INGESTION_ATTEMPTS
        ):
            raise ValueError("Invalid ingestion attempt count.")
        if (
            self.state not in ("queued", "running", "succeeded", "failed", "cancelled")
            or not self.pipeline_version
        ):
            raise ValueError("Invalid ingestion job state.")
        if self.state == "running" and (self.lease_owner is None or self.lease_until is None):
            raise ValueError("Running jobs require a live fenced lease.")
        utc(self.run_after, self.lease_until, self.heartbeat_at, self.created_at)
