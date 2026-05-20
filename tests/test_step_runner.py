from pm_tests.core.models import AdapterError, StepPlan, Status
from pm_tests.core.ports import AdapterResult
from pm_tests.core.runner import StepRunner


class FakeTrafficPort:
    def run_step(self, step):
        return AdapterResult(
            success=True,
            message="ok",
            metrics={"success_count": 5},
            artifacts=[],
            data={"raw": "5 packets received"},
        )


class FailingPort:
    def run_step(self, step):
        return AdapterResult(
            success=False,
            message="failed",
            error=AdapterError(
                code="FAKE_FAILED",
                message="fake failure",
                adapter="fake",
                recoverable=False,
            ),
        )


def test_step_runner_records_success():
    runner = StepRunner({"traffic": FakeTrafficPort()})
    record = runner.run(StepPlan(step_id="ping", kind="ping", adapter="traffic"))

    assert record.status == Status.PASSED
    assert record.metrics["success_count"] == 5
    assert record.error is None


def test_step_runner_records_adapter_failure():
    runner = StepRunner({"fake": FailingPort()})
    record = runner.run(StepPlan(step_id="x", kind="x", adapter="fake"))

    assert record.status == Status.FAILED
    assert record.error.code == "FAKE_FAILED"


def test_step_runner_maps_missing_adapter_to_error():
    runner = StepRunner({})
    record = runner.run(StepPlan(step_id="missing", kind="x", adapter="none"))

    assert record.status == Status.ERROR
    assert record.error.code == "ADAPTER_NOT_FOUND"
