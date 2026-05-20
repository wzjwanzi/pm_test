"""Run orchestration and case execution."""
from __future__ import annotations

import json
import threading
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from pm_tests.core.models import (
    AdapterError,
    CasePlan,
    CaseRecord,
    RunPlan,
    RunRecord,
    StepRecord,
    Status,
    to_serializable,
    utc_now_iso,
)
from pm_tests.core.payloads import externalize_large_step_payloads
from pm_tests.core.ports import StepPort
from pm_tests.core.runner import StepRunner
from pm_tests.core.store import RunStore


CLEANUP_WARNING = "执行结束会尝试清理"


class CaseExecutor:
    """Execute one case plan and collect step records."""

    def __init__(self, step_runner: StepRunner, store: RunStore):
        self.step_runner = step_runner
        self.store = store

    def execute(
        self,
        run_id: str,
        case_plan: CasePlan,
        case_dir: Path,
        on_update: Callable[[CaseRecord], None] | None = None,
    ) -> CaseRecord:
        record = CaseRecord(
            case_id=case_plan.case_id,
            name=case_plan.name,
            status=Status.RUNNING,
            started_at=utc_now_iso(),
            artifact_dir=case_dir,
            metadata=dict(case_plan.metadata),
        )
        case_dir.mkdir(parents=True, exist_ok=True)
        execution_log = case_dir.parent.parent / "execution.log"
        self._append_execution_log(
            execution_log,
            f"case_start run_id={run_id} case={case_plan.name} case_id={case_plan.case_id} step_count={len(case_plan.step_plans)}",
        )
        if on_update:
            on_update(record)

        for step in case_plan.step_plans:
            if self.store.stop_requested(run_id):
                record.status = Status.STOPPED
                self._append_execution_log(execution_log, f"case_stopped case={case_plan.name}")
                break
            step = self._with_case_output_dir(step, case_dir)
            self._append_execution_log(
                execution_log,
                (
                    f"step_start case={case_plan.name} step={step.step_id} "
                    f"action={step.action or step.kind} adapter={step.adapter} params={self._summarize_params(step.parameters)}"
                ),
            )
            step_record = self.step_runner.run(step)
            externalize_large_step_payloads(step_record, case_dir)
            record.step_records.append(step_record)
            if on_update:
                on_update(record)
            self._append_execution_log(
                execution_log,
                (
                    f"step_end case={case_plan.name} step={step.step_id} status={step_record.status} "
                    f"message={step_record.message} error={self._summarize_error(step_record)} "
                    f"{self._summarize_step_data(step_record)} artifacts={self._summarize_artifacts(step_record)}"
                ),
            )
            for detail in self._summarize_nested_results(step_record):
                self._append_execution_log(execution_log, detail)

        for cleanup_record in self._cleanup_open_explicit_sessions(case_dir):
            externalize_large_step_payloads(cleanup_record, case_dir)
            record.step_records.append(cleanup_record)
            warnings = record.metadata.setdefault("warnings", [])
            if CLEANUP_WARNING not in warnings:
                warnings.append(CLEANUP_WARNING)
            if on_update:
                on_update(record)

        if record.status != Status.STOPPED:
            if any(step.status in {Status.FAILED, Status.ERROR} for step in record.step_records):
                record.status = Status.FAILED
            else:
                record.status = Status.PASSED
        record.ended_at = utc_now_iso()
        self._write_json(case_dir / "case.json", record)
        self._append_execution_log(
            execution_log,
            f"case_end run_id={run_id} case={case_plan.name} status={record.status} artifact_dir={case_dir}",
        )
        if on_update:
            on_update(record)
        return record

    def _with_case_output_dir(self, step, case_dir: Path):
        params = dict(step.parameters or {})
        case_dir_text = str(case_dir)
        if step.adapter == "base_web":
            params["download_dir"] = case_dir_text
            params["web_capture_download_dir"] = case_dir_text
            params["web_log_download_dir"] = case_dir_text
        elif step.adapter == "ssh":
            params["ssh_log_output_dir"] = case_dir_text
            params["log_output_dir"] = case_dir_text
        elif step.adapter == "capture":
            params["case_dir"] = case_dir_text
        else:
            return step
        return replace(step, parameters=params)

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(to_serializable(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_execution_log(self, path: Path, message: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now_iso()} {message}\n")

    def _summarize_params(self, params: dict) -> str:
        redacted = {}
        for key, value in dict(params or {}).items():
            if "password" in str(key).lower():
                redacted[key] = "***"
            else:
                redacted[key] = value
        text = json.dumps(redacted, ensure_ascii=False, default=str)
        return text[:1000]

    def _summarize_error(self, record: StepRecord) -> str:
        if not record.error:
            return ""
        return json.dumps(to_serializable(record.error), ensure_ascii=False, default=str)[:1000]

    def _summarize_step_data(self, record: StepRecord) -> str:
        parts = []
        data = record.data or {}
        for key in ("operation", "command", "commands", "stdout", "stderr", "results", "stopped", "local_path", "remote_path"):
            value = data.get(key)
            if value in (None, ""):
                continue
            parts.append(f"{key}={self._summarize_value(value)}")
        return " ".join(parts)

    def _summarize_value(self, value) -> str:
        if isinstance(value, (dict, list, tuple)):
            text = json.dumps(to_serializable(value), ensure_ascii=False, default=str)
        else:
            text = str(value)
        return text.replace("\r", "\\r").replace("\n", "\\n")[:1000]

    def _summarize_nested_results(self, record: StepRecord) -> list[str]:
        results = (record.data or {}).get("results")
        if not isinstance(results, list):
            return []
        details = []
        for index, item in enumerate(results, start=1):
            if not isinstance(item, dict):
                continue
            parts = []
            command = item.get("command")
            stdout = item.get("stdout")
            stderr = item.get("stderr")
            exit_status = item.get("exit_status")
            if command not in (None, ""):
                parts.append(f"result[{index}].input={self._summarize_value(command)}")
            if stdout not in (None, ""):
                parts.append(f"result[{index}].stdout={self._summarize_value(stdout)}")
            if stderr not in (None, ""):
                parts.append(f"result[{index}].stderr={self._summarize_value(stderr)}")
            if exit_status not in (None, ""):
                parts.append(f"result[{index}].exit_status={self._summarize_value(exit_status)}")
            if parts:
                details.append(" ".join(parts))
        return details

    def _summarize_artifacts(self, record: StepRecord) -> str:
        if not record.artifacts:
            return ""
        return json.dumps(to_serializable(record.artifacts), ensure_ascii=False, default=str)[:1000]

    def _cleanup_open_explicit_sessions(self, case_dir: Path) -> list[StepRecord]:
        records: list[StepRecord] = []
        for adapter_name, adapter in self.step_runner.adapters.items():
            cleanup = getattr(adapter, "cleanup_open_explicit_sessions", None)
            if not callable(cleanup):
                continue
            started_at = utc_now_iso()
            try:
                results = cleanup() or []
            except Exception as exc:
                records.append(
                    StepRecord(
                        step_id=f"cleanup_{adapter_name}",
                        kind="cleanup_explicit_sessions",
                        adapter=adapter_name,
                        status=Status.ERROR,
                        started_at=started_at,
                        ended_at=utc_now_iso(),
                        message=CLEANUP_WARNING,
                        data={
                            "warning": CLEANUP_WARNING,
                            "cleanup_success": False,
                            "exception_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                )
                continue
            for index, result in enumerate(results, start=1):
                records.append(
                    StepRecord(
                        step_id=f"cleanup_{adapter_name}_{index}",
                        kind="cleanup_explicit_sessions",
                        adapter=adapter_name,
                        status=Status.PASSED if result.success else Status.FAILED,
                        started_at=started_at,
                        ended_at=utc_now_iso(),
                        message=CLEANUP_WARNING,
                        metrics=dict(result.metrics),
                        artifacts=list(result.artifacts),
                        data={
                            **dict(result.data),
                            "warning": CLEANUP_WARNING,
                            "cleanup_success": bool(result.success),
                            "case_dir": str(case_dir),
                        },
                    )
                )
        return records


class RunOrchestrator:
    """Create, execute, and query PM runs."""

    def __init__(
        self,
        *,
        artifacts_root: str | Path,
        adapters: dict[str, StepPort],
        run_async: bool = True,
        store: RunStore | None = None,
    ):
        self.artifacts_root = Path(artifacts_root)
        self.adapters = adapters
        self.run_async = run_async
        self.store = store or RunStore()
        self.step_runner = StepRunner(adapters)
        self.case_executor = CaseExecutor(self.step_runner, self.store)

    def create_run(self, plan: RunPlan) -> RunRecord:
        artifact_dir = self.artifacts_root / plan.run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        self._append_run_log(artifact_dir, f"run_start run_id={plan.run_id} device_id={plan.device_id} case_count={len(plan.case_plans)}")
        record = RunRecord.from_plan(plan, artifact_dir=artifact_dir)
        self.store.put(record)
        if self.run_async:
            worker = threading.Thread(
                target=self._execute_run,
                args=(plan,),
                name=f"pm-run-{plan.run_id}",
                daemon=True,
            )
            worker.start()
            return self.store.get(plan.run_id) or record
        self._execute_run(plan)
        return self.store.get(plan.run_id) or record

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.store.get(run_id)

    def list_runs(self, limit: int = 20) -> list[RunRecord]:
        return self.store.list(limit)

    def request_stop(self, run_id: str) -> RunRecord | None:
        return self.store.request_stop(run_id)

    def _execute_run(self, plan: RunPlan) -> None:
        record = self.store.get(plan.run_id)
        if not record:
            return
        record.status = Status.RUNNING
        record.started_at = utc_now_iso()
        record.case_records = []
        self.store.put(record)

        try:
            cases_dir = Path(record.artifact_dir) / "cases"
            for index, case_plan in enumerate(plan.case_plans, start=1):
                if self.store.stop_requested(plan.run_id):
                    record.status = Status.STOPPED
                    break
                case_dir = self._case_output_dir(cases_dir, case_plan, index)
                completed_cases = list(record.case_records)

                def on_case_update(case_record: CaseRecord) -> None:
                    live_record = self.store.get(plan.run_id) or record
                    live_record.status = Status.RUNNING
                    live_record.started_at = record.started_at
                    live_record.case_records = completed_cases + [case_record]
                    live_record.progress = {"current": index, "total": len(plan.case_plans)}
                    self.store.put(live_record)
                    self._write_run(live_record)

                case_record = self.case_executor.execute(plan.run_id, case_plan, case_dir, on_update=on_case_update)
                record.case_records = completed_cases + [case_record]
                record.progress = {"current": index, "total": len(plan.case_plans)}
                self.store.put(record)

            if record.status != Status.STOPPED:
                record.status = self._final_status(record.case_records)
            record.summary = self._build_summary(record.case_records)
        except Exception as exc:
            record.status = Status.ERROR
            record.error = AdapterError(
                code="RUN_EXECUTION_ERROR",
                message=str(exc),
                adapter="orchestrator",
                recoverable=False,
                details={"exception_type": type(exc).__name__},
            )
            record.summary = self._build_summary(record.case_records)
            self._append_run_log(Path(record.artifact_dir), f"run_error run_id={plan.run_id} error={exc} exception_type={type(exc).__name__}")
        finally:
            record.ended_at = utc_now_iso()
            self._write_run(record)
            self._append_run_log(
                Path(record.artifact_dir),
                f"run_end run_id={plan.run_id} status={record.status} summary={json.dumps(record.summary, ensure_ascii=False)}",
            )
            self.store.put(record)

    def _final_status(self, cases: list[CaseRecord]) -> Status:
        if any(case.status in {Status.FAILED, Status.ERROR} for case in cases):
            return Status.FAILED
        if all(case.status == Status.PASSED for case in cases):
            return Status.PASSED
        return Status.ERROR

    def _build_summary(self, cases: list[CaseRecord]) -> dict[str, int]:
        return {
            "total": len(cases),
            "passed": sum(1 for case in cases if case.status == Status.PASSED),
            "failed": sum(1 for case in cases if case.status == Status.FAILED),
            "error": sum(1 for case in cases if case.status == Status.ERROR),
            "skipped": sum(1 for case in cases if case.status == Status.SKIPPED),
        }

    def _write_run(self, record: RunRecord) -> None:
        path = Path(record.artifact_dir) / "run.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(to_serializable(record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _case_output_dir(self, cases_dir: Path, case_plan: CasePlan, index: int) -> Path:
        base_name = _case_output_folder_name(case_plan.name or case_plan.case_id)
        candidate = cases_dir / base_name
        suffix = 2
        while candidate.exists():
            candidate = cases_dir / f"{base_name}_{suffix}"
            suffix += 1
        return candidate

    def _append_run_log(self, artifact_dir: Path, message: str) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        with (artifact_dir / "execution.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now_iso()} {message}\n")


def _case_output_folder_name(case_name: str) -> str:
    safe_name = _safe_path_segment(case_name) or "case"
    return f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _safe_path_segment(value: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = []
    for char in str(value or "").strip():
        if char in invalid or ord(char) < 32:
            cleaned.append("_")
        elif char.isspace():
            cleaned.append("_")
        else:
            cleaned.append(char)
    text = "".join(cleaned).strip("._ ")
    while "__" in text:
        text = text.replace("__", "_")
    return text[:80]
