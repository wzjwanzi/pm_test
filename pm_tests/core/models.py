"""Typed plans and records for PM execution."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class Status(StrEnum):
    """Stable lifecycle states used by runs, cases, and steps."""

    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    STOPPING = "stopping"
    STOPPED = "stopped"


def utc_now_iso() -> str:
    """Return a UTC ISO timestamp without microseconds."""

    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def to_serializable(value: Any) -> Any:
    """Convert dataclasses and common value objects into JSON-ready data."""

    if isinstance(value, StrEnum):
        return str(value)
    if is_dataclass(value):
        return {item.name: to_serializable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_serializable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


@dataclass(slots=True)
class AdapterError:
    code: str
    message: str
    adapter: str
    recoverable: bool = False
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Artifact:
    kind: str
    path: Path | str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepPlan:
    step_id: str
    kind: str
    adapter: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    required: bool = True
    action: str = ""
    label: str = ""


@dataclass(slots=True)
class CasePlan:
    case_id: str
    name: str
    step_plans: list[StepPlan] = field(default_factory=list)
    assertions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunPlan:
    run_id: str
    device_id: str
    case_plans: list[CasePlan] = field(default_factory=list)
    settings_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepRecord:
    step_id: str
    kind: str
    adapter: str
    status: Status
    started_at: str
    ended_at: str | None = None
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: AdapterError | None = None


@dataclass(slots=True)
class CaseRecord:
    case_id: str
    name: str
    status: Status
    started_at: str | None = None
    ended_at: str | None = None
    step_records: list[StepRecord] = field(default_factory=list)
    assertion_results: dict[str, bool] = field(default_factory=dict)
    pre_snapshot: dict[str, Any] = field(default_factory=dict)
    post_snapshot: dict[str, Any] = field(default_factory=dict)
    artifact_dir: Path | str | None = None
    error: AdapterError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    device_id: str
    status: Status
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    progress: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, int] = field(default_factory=dict)
    artifact_dir: Path | str | None = None
    case_records: list[CaseRecord] = field(default_factory=list)
    error: AdapterError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_plan(cls, plan: RunPlan, artifact_dir: Path | str) -> "RunRecord":
        case_records = [
            CaseRecord(
                case_id=case.case_id,
                name=case.name,
                status=Status.QUEUED,
                metadata=dict(case.metadata),
            )
            for case in plan.case_plans
        ]
        return cls(
            run_id=plan.run_id,
            device_id=plan.device_id,
            status=Status.QUEUED,
            created_at=utc_now_iso(),
            progress={"current": 0, "total": len(plan.case_plans)},
            summary={
                "total": len(plan.case_plans),
                "passed": 0,
                "failed": 0,
                "error": 0,
                "skipped": 0,
            },
            artifact_dir=artifact_dir,
            case_records=case_records,
            metadata=dict(plan.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(self)
