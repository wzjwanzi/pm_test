"""In-memory run manager for PM tests."""

from __future__ import annotations

import threading
import uuid
from collections import deque
from pathlib import Path
from typing import Callable

from .models import PingCaseSpec, RunRecord, utc_now_iso

RunExecutor = Callable[[RunRecord, list[PingCaseSpec]], None]


class InMemoryRunManager:
    """Manage PM test runs in memory and execute them in background threads."""

    def __init__(self, executor: RunExecutor, *, artifacts_root: str | Path = "artifacts/pm_runs", max_runs: int = 50):
        self.executor = executor
        self.artifacts_root = Path(artifacts_root)
        self.max_runs = max_runs
        self._runs: dict[str, RunRecord] = {}
        self._order: deque[str] = deque()
        self._lock = threading.RLock()

    def create_run(
        self,
        device_id: str,
        cases: list[PingCaseSpec],
        *,
        metadata: dict | None = None,
    ) -> RunRecord:
        run_id = uuid.uuid4().hex
        artifact_dir = self.artifacts_root / run_id
        record = RunRecord(
            run_id=run_id,
            device_id=device_id,
            status="queued",
            created_at=utc_now_iso(),
            artifact_dir=str(artifact_dir),
            metadata=metadata or {},
        )

        with self._lock:
            self._runs[run_id] = record
            self._order.appendleft(run_id)
            while len(self._order) > self.max_runs:
                stale_id = self._order.pop()
                self._runs.pop(stale_id, None)

        worker = threading.Thread(
            target=self._execute_run,
            args=(record, list(cases)),
            name=f"pm-run-{run_id[:8]}",
            daemon=True,
        )
        worker.start()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        with self._lock:
            run_ids = list(self._order)[: max(limit, 0)]
            return [self._runs[run_id] for run_id in run_ids if run_id in self._runs]

    def _execute_run(self, record: RunRecord, cases: list[PingCaseSpec]) -> None:
        try:
            self.executor(record, cases)
        except Exception as exc:  # pragma: no cover - defensive
            record.status = "error"
            record.error = str(exc)
            record.ended_at = utc_now_iso()
