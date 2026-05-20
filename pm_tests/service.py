"""Flask-callable PM test service."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .capture import DeviceTcpdumpCaptureBackend, start_capture_with_fallback
from .models import CaseResult, PingCaseSpec, RunRecord, to_serializable, utc_now_iso
from .ping import DevicePingExecutor
from .run_manager import InMemoryRunManager
from .snapshots import SnapshotCollector


class PMTestService:
    """MVP execution facade for ping batch runs."""

    def __init__(
        self,
        *,
        artifacts_root: str | Path = "artifacts/pm_runs",
        capture_backend: DeviceTcpdumpCaptureBackend | None = None,
        snapshot_collector: SnapshotCollector | None = None,
        ping_executor: DevicePingExecutor | None = None,
    ):
        self.artifacts_root = Path(artifacts_root)
        self.capture_backend = capture_backend or DeviceTcpdumpCaptureBackend()
        self.snapshot_collector = snapshot_collector or SnapshotCollector()
        self.ping_executor = ping_executor or DevicePingExecutor()
        self._device_locks: dict[str, threading.Lock] = {}
        self._device_locks_guard = threading.Lock()
        self.run_manager = InMemoryRunManager(self._execute_run, artifacts_root=self.artifacts_root)

    def create_run(
        self,
        device_id: str,
        cases: list[PingCaseSpec | dict[str, Any]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_cases = [self._coerce_case(item) for item in cases]
        record = self.run_manager.create_run(device_id, normalized_cases, metadata=metadata)
        return record.to_dict()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        record = self.run_manager.get_run(run_id)
        return record.to_dict() if record else None

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.run_manager.list_runs(limit)]

    def _execute_run(self, record: RunRecord, cases: list[PingCaseSpec]) -> None:
        artifact_root = Path(record.artifact_dir or self.artifacts_root / record.run_id)
        artifact_root.mkdir(parents=True, exist_ok=True)

        device_lock = self._get_device_lock(record.device_id)
        with device_lock:
            record.status = "running"
            record.started_at = utc_now_iso()
            self._write_json(artifact_root / "run.json", record.to_dict())

            for index, case in enumerate(cases, start=1):
                case_result = self._execute_case(record.device_id, case, artifact_root, index)
                record.cases.append(case_result)
                self._write_json(artifact_root / "run.json", record.to_dict())

            record.status = "completed"
            if any(not item.passed for item in record.cases):
                record.status = "failed"
            record.ended_at = utc_now_iso()
            self._write_json(artifact_root / "run.json", record.to_dict())

    def _execute_case(
        self,
        device_id: str,
        case: PingCaseSpec,
        artifact_root: Path,
        index: int,
    ) -> CaseResult:
        case_dir = artifact_root / f"{index:03d}_{case.case_id}"
        case_dir.mkdir(parents=True, exist_ok=True)

        result = CaseResult(
            case_id=case.case_id,
            name=case.name,
            status="running",
            started_at=utc_now_iso(),
            artifact_dir=str(case_dir),
            metadata=dict(case.metadata),
        )

        capture_session = None
        try:
            result.pre_snapshot = self.snapshot_collector.collect(device_id)
            capture_session = start_capture_with_fallback(self.capture_backend, device_id, case_dir, host=case.host)
            result.ping = self.ping_executor.run(device_id, case)
            result.post_snapshot = self.snapshot_collector.collect(device_id)
            result.capture = capture_session.stop()

            ping_ok = bool(result.ping and result.ping.success_count >= case.normalized_count() and result.ping.timeout_count == 0)
            capture_ok = bool(result.capture and result.capture.succeeded)

            result.assertions = {
                "ping_5_of_5_success": ping_ok,
                "capture_succeeded": capture_ok,
            }
            result.passed = ping_ok and (capture_ok or not case.require_capture)
            result.status = "passed" if result.passed else "failed"
        except Exception as exc:
            result.status = "error"
            result.error = str(exc)
            if capture_session is not None:
                try:
                    result.capture = capture_session.stop()
                except Exception:  # pragma: no cover - defensive
                    pass
        finally:
            result.ended_at = utc_now_iso()
            self._write_json(case_dir / "case.json", to_serializable(result))
        return result

    def _coerce_case(self, value: PingCaseSpec | dict[str, Any]) -> PingCaseSpec:
        if isinstance(value, PingCaseSpec):
            return value

        data = dict(value)
        return PingCaseSpec(
            case_id=str(data.get("case_id") or data.get("name") or "case"),
            name=str(data.get("name") or data.get("case_id") or "Ping Case"),
            host=str(data.get("host") or "8.8.8.8"),
            count=int(data.get("count") or 5),
            timeout_seconds=int(data.get("timeout_seconds") or 30),
            require_capture=bool(data.get("require_capture", False)),
            metadata=dict(data.get("metadata") or {}),
        )

    def _get_device_lock(self, device_id: str) -> threading.Lock:
        with self._device_locks_guard:
            if device_id not in self._device_locks:
                self._device_locks[device_id] = threading.Lock()
            return self._device_locks[device_id]

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def create_default_service(*, artifacts_root: str | Path = "artifacts/pm_runs") -> PMTestService:
    """Convenience factory for Flask integration."""

    return PMTestService(artifacts_root=artifacts_root)
