from pathlib import Path

from pm_tests.core.models import (
    AdapterError,
    Artifact,
    CasePlan,
    RunPlan,
    RunRecord,
    StepPlan,
    StepRecord,
    Status,
    to_serializable,
    utc_now_iso,
)


def test_model_serialization_preserves_chinese_and_paths():
    plan = RunPlan(
        run_id="run-1",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="默认Ping业务",
                step_plans=[
                    StepPlan(
                        step_id="ping",
                        kind="ping",
                        adapter="traffic",
                        parameters={"host": "10.0.0.1"},
                    )
                ],
            )
        ],
    )
    record = RunRecord.from_plan(plan, artifact_dir=Path("artifacts/test_runs/run-1"))

    data = to_serializable(record)

    assert data["run_id"] == "run-1"
    assert data["device_id"] == "device-1"
    assert data["artifact_dir"].endswith("artifacts/test_runs/run-1")
    assert data["case_records"][0]["name"] == "默认Ping业务"


def test_step_record_can_store_structured_error_and_artifacts():
    error = AdapterError(
        code="ADB_SHELL_FAILED",
        message="执行 adb shell 失败",
        adapter="adb",
        recoverable=True,
        details={"command": "ping -c 1 10.0.0.1"},
    )
    step = StepRecord(
        step_id="ping",
        kind="ping",
        adapter="traffic",
        status=Status.ERROR,
        started_at=utc_now_iso(),
        ended_at=utc_now_iso(),
        message="Ping failed",
        artifacts=[Artifact(kind="log", path=Path("ping.log"))],
        error=error,
    )

    data = to_serializable(step)

    assert data["status"] == "error"
    assert data["error"]["code"] == "ADB_SHELL_FAILED"
    assert data["artifacts"][0]["path"] == "ping.log"
