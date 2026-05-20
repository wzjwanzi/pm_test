"""Compatibility facade exposing the active PM execution service."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from app_settings import load_runtime_settings
from desktop.case_library import CaseLibrary
from desktop.case_templates import build_default_case_templates
from pm_tests.core.adapters import build_default_adapters
from pm_tests.core.models import RunRecord, Status, StepPlan, to_serializable
from pm_tests.core.orchestrator import RunOrchestrator
from pm_tests.core.planner import build_run_plan
from pm_tests.core.ports import AdapterResult


class NoopAdapter:
    """Adapter used for unit and compatibility paths without hardware."""

    def run_step(self, step: StepPlan) -> AdapterResult:
        return AdapterResult(
            success=True,
            message=f"{step.step_id} skipped by noop adapter.",
            data={
                "skipped": True,
                "action": step.action,
                "label": step.label,
            },
        )


class PmTestRunManager:
    """Facade compatible with the previous PmTestRunManager name."""

    def __init__(
        self,
        *,
        artifacts_root: str | Path | None = None,
        run_async: bool = True,
        adapters: dict[str, Any] | None = None,
    ):
        self.artifacts_root = Path(artifacts_root or config.PM_ARTIFACTS_DIR)
        self.run_async = run_async
        self._adapters_override = adapters
        self._orchestrators: dict[str, RunOrchestrator] = {}

    def get_templates(self) -> list[dict]:
        settings = load_runtime_settings()
        saved_cases = CaseLibrary().list_cases()
        if saved_cases:
            return [case.to_dict() for case in saved_cases]
        return [case.to_dict() for case in build_default_case_templates(settings)]

    def inspect_device(self, device_id: str) -> dict:
        return {
            "success": True,
            "device_id": device_id,
            "message": "Device inspection is available through the new adapter model.",
        }

    def create_run(self, device_id: str, cases: list[dict] | None = None) -> dict:
        settings_snapshot = load_runtime_settings()
        plan = build_run_plan(
            device_id,
            cases or [],
            settings_snapshot,
        )
        orchestrator = RunOrchestrator(
            artifacts_root=self.artifacts_root,
            adapters=self._build_adapters(device_id),
            run_async=self.run_async,
        )
        self._orchestrators[plan.run_id] = orchestrator
        record = orchestrator.create_run(plan)
        return {
            "success": True,
            "run": self._legacy_run(record),
        }

    def request_stop(self, run_id: str) -> dict | None:
        orchestrator = self._orchestrators.get(run_id)
        if not orchestrator:
            return None
        record = orchestrator.request_stop(run_id)
        return self._legacy_run(record) if record else None

    def get_run(self, run_id: str) -> dict | None:
        orchestrator = self._orchestrators.get(run_id)
        if not orchestrator:
            return None
        record = orchestrator.get_run(run_id)
        return self._legacy_run(record) if record else None

    def list_runs(self, limit: int = 20) -> list[dict]:
        records: list[RunRecord] = []
        for orchestrator in self._orchestrators.values():
            records.extend(orchestrator.list_runs(limit=limit))
        records.sort(key=lambda item: item.created_at, reverse=True)
        return [self._legacy_run(record) for record in records[:limit]]

    def _build_adapters(self, device_id: str) -> dict[str, Any]:
        if self._adapters_override is not None:
            return self._adapters_override
        if not self.run_async:
            noop = NoopAdapter()
            return {
                "snapshot": noop,
                "traffic": noop,
                "base_web": noop,
                "ssh": noop,
                "capture": noop,
                "traffic_server": noop,
            }
        return build_default_adapters(device_id)

    def _legacy_run(self, record: RunRecord) -> dict:
        data = to_serializable(record)
        data["state"] = data["status"]
        data["case_total"] = data["summary"].get("total", len(data.get("case_records", [])))
        data["results"] = [
            {
                "case_id": case["case_id"],
                "name": case["name"],
                "status": case["status"],
                "passed": case["status"] == Status.PASSED,
                "steps": [
                    f"{step['step_id']}: {step['status']} {step.get('message', '')}".strip()
                    for step in case.get("step_records", [])
                ],
                "step_records": case.get("step_records", []),
                "artifact_dir": case.get("artifact_dir"),
                "error": case.get("error"),
            }
            for case in data.get("case_records", [])
        ]
        current_case = next(
            (case for case in data.get("case_records", []) if case.get("status") == Status.RUNNING),
            None,
        )
        data["current_case_name"] = current_case.get("name") if current_case else None
        data["current_steps"] = [
            f"{step['step_id']}: {step['status']}"
            for step in (current_case or {}).get("step_records", [])
        ]
        return data
