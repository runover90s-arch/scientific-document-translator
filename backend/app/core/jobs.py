from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass
class JobRecord:
    id: str
    status: str = "queued"
    filename: str = ""
    source_language: str = "auto"
    target_language: str = "vi"
    output_format: str = "html"
    progress: int = 0
    message: str = "Queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    outputs: dict[str, str] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Internal representation. Output values are local filesystem paths."""
        return asdict(self)

    def to_public_dict(self) -> dict[str, Any]:
        """API-safe representation. Never expose server filesystem paths."""
        data = asdict(self)
        data["outputs"] = {
            fmt: f"/api/v1/jobs/{self.id}/download/{fmt}"
            for fmt in self.outputs
        }
        return data


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, record: JobRecord) -> JobRecord:
        with self._lock:
            self._jobs[record.id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: Any) -> JobRecord:
        with self._lock:
            record = self._jobs[job_id]
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(timezone.utc).isoformat()
            return record


job_store = JobStore()
