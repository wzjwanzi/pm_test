"""Step execution and normalization."""
from __future__ import annotations

from collections.abc import Mapping

from pm_tests.core.models import AdapterError, StepPlan, StepRecord, Status, utc_now_iso
from pm_tests.core.ports import AdapterResult, StepPort


class StepRunner:
    """Run one step through an adapter and normalize the result."""

    def __init__(self, adapters: Mapping[str, StepPort]):
        self.adapters = adapters

    def run(self, step: StepPlan) -> StepRecord:
        started_at = utc_now_iso()
        adapter = self.adapters.get(step.adapter)
        if adapter is None:
            return StepRecord(
                step_id=step.step_id,
                kind=step.kind,
                adapter=step.adapter,
                status=Status.ERROR,
                started_at=started_at,
                ended_at=utc_now_iso(),
                message=f"Adapter '{step.adapter}' was not found.",
                error=AdapterError(
                    code="ADAPTER_NOT_FOUND",
                    message=f"Adapter '{step.adapter}' was not found.",
                    adapter=step.adapter,
                    recoverable=False,
                ),
            )

        try:
            result = adapter.run_step(step)
        except Exception as exc:
            return StepRecord(
                step_id=step.step_id,
                kind=step.kind,
                adapter=step.adapter,
                status=Status.ERROR,
                started_at=started_at,
                ended_at=utc_now_iso(),
                message=str(exc),
                error=AdapterError(
                    code="ADAPTER_EXCEPTION",
                    message=str(exc),
                    adapter=step.adapter,
                    recoverable=False,
                    details={"exception_type": type(exc).__name__},
                ),
            )

        return self._record_from_result(step, started_at, result)

    def _record_from_result(self, step: StepPlan, started_at: str, result: AdapterResult) -> StepRecord:
        status = Status.PASSED if result.success else Status.FAILED
        if not result.success and not step.required:
            status = Status.SKIPPED
        data = dict(result.data)
        data.setdefault("operation", step.action or step.kind)
        if "command" in step.parameters and step.parameters.get("command") and "command" not in data:
            data["command"] = step.parameters.get("command")
        if "commands" in step.parameters and step.parameters.get("commands") and "commands" not in data:
            data["commands"] = step.parameters.get("commands")
        if step.label and "label" not in data:
            data["label"] = step.label
        return StepRecord(
            step_id=step.step_id,
            kind=step.kind,
            adapter=step.adapter,
            status=status,
            started_at=started_at,
            ended_at=utc_now_iso(),
            message=result.message,
            metrics=dict(result.metrics),
            artifacts=list(result.artifacts),
            data=data,
            error=None if status == Status.SKIPPED else result.error,
        )
