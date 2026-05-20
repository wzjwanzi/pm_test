"""Thread-safe in-memory run store."""
from __future__ import annotations

import copy
import threading
from collections import deque

from pm_tests.core.models import RunRecord, Status


class RunStore:
    """Store recent run records in memory."""

    def __init__(self, max_runs: int = 50):
        self.max_runs = max_runs
        self._runs: dict[str, RunRecord] = {}
        self._order: deque[str] = deque()
        self._stop_requested: set[str] = set()
        self._lock = threading.RLock()

    def put(self, record: RunRecord) -> RunRecord:
        with self._lock:
            is_new = record.run_id not in self._runs
            self._runs[record.run_id] = copy.deepcopy(record)
            if is_new:
                self._order.appendleft(record.run_id)
            while len(self._order) > self.max_runs:
                stale_id = self._order.pop()
                self._runs.pop(stale_id, None)
                self._stop_requested.discard(stale_id)
            return copy.deepcopy(self._runs[record.run_id])

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            return copy.deepcopy(record) if record else None

    def list(self, limit: int = 20) -> list[RunRecord]:
        with self._lock:
            run_ids = list(self._order)[: max(limit, 0)]
            return [copy.deepcopy(self._runs[run_id]) for run_id in run_ids if run_id in self._runs]

    def request_stop(self, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            self._stop_requested.add(run_id)
            if record.status not in {Status.PASSED, Status.FAILED, Status.ERROR, Status.STOPPED}:
                record.status = Status.STOPPING
            return copy.deepcopy(record)

    def stop_requested(self, run_id: str) -> bool:
        with self._lock:
            return run_id in self._stop_requested
