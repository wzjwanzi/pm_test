"""Data models for PM test execution."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: to_serializable(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_serializable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


@dataclass(slots=True)
class PingCaseSpec:
    """Input spec for a single ping case."""

    case_id: str
    name: str
    host: str
    count: int = 5
    timeout_seconds: int = 30
    require_capture: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized_count(self) -> int:
        return max(int(self.count or 5), 1)


@dataclass(slots=True)
class NetworkSnapshot:
    """Device/network snapshot before or after a case."""

    captured_at: str
    network_type: str | None = None
    signal: dict[str, Any] = field(default_factory=dict)
    cell_info: dict[str, Any] = field(default_factory=dict)
    network_info: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CaptureRecord:
    """Packet capture status for one case."""

    backend: str
    status: str
    started_at: str | None = None
    stopped_at: str | None = None
    privilege: str | None = None
    remote_pcap_path: str | None = None
    local_pcap_path: str | None = None
    local_log_path: str | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "captured"


@dataclass(slots=True)
class PingResult:
    """Ping execution outcome."""

    status: str
    host: str
    count: int
    started_at: str
    ended_at: str
    success_count: int
    timeout_count: int
    packet_loss_percent: float | None
    return_code: int | None
    stats: dict[str, Any] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)
    raw_output: str = ""
    error: str | None = None

    @property
    def all_success(self) -> bool:
        return self.success_count >= self.count and self.timeout_count == 0 and self.status == "completed"


@dataclass(slots=True)
class CaseResult:
    """Stored result for a single case inside a run."""

    case_id: str
    name: str
    status: str
    started_at: str
    ended_at: str | None = None
    artifact_dir: str | None = None
    pre_snapshot: NetworkSnapshot | None = None
    post_snapshot: NetworkSnapshot | None = None
    capture: CaptureRecord | None = None
    ping: PingResult | None = None
    passed: bool = False
    assertions: dict[str, bool] = field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunRecord:
    """Top-level batch run."""

    run_id: str
    device_id: str
    status: str
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    artifact_dir: str | None = None
    cases: list[CaseResult] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = to_serializable(self)
        cases = data.get("cases", [])
        data["summary"] = {
            "total": len(cases),
            "passed": sum(1 for item in cases if item.get("passed")),
            "failed": sum(1 for item in cases if item.get("status") in {"failed", "error"}),
            "completed": sum(1 for item in cases if item.get("status") in {"passed", "failed", "error"}),
        }
        return data
