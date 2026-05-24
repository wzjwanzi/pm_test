from pathlib import Path
import json
import re
import threading
import time

from pm_tests.core.models import CasePlan, RunPlan, StepPlan, Status
from pm_tests.core.orchestrator import RunOrchestrator
from pm_tests.core.ports import AdapterResult


class PassingPort:
    def run_step(self, step):
        return AdapterResult(success=True, message=f"{step.step_id} ok")


class FailingPort:
    def run_step(self, step):
        return AdapterResult(success=False, message="failed")


class CommandPort:
    def run_step(self, step):
        return AdapterResult(
            success=True,
            message="command completed",
            data={"command": step.parameters["command"], "stdout": "hello", "stderr": "warn"},
        )


class RepeatResultPort:
    def run_step(self, step):
        return AdapterResult(
            success=True,
            message="repeat completed",
            data={
                "results": [
                    {"command": "cmd-1", "stdout": "out-1", "stderr": "", "exit_status": 0},
                    {"command": "cmd-2", "stdout": "", "stderr": "err-2", "exit_status": 1},
                ]
            },
        )


class RecordingPort:
    def __init__(self):
        self.calls = []

    def run_step(self, step):
        self.calls.append((step.adapter, dict(step.parameters)))
        return AdapterResult(
            success=True,
            message="recorded",
            data={"local_path": str(Path(step.parameters.get("ssh_log_output_dir") or step.parameters.get("download_dir") or step.parameters.get("case_dir") or "") / "artifact.log")},
        )


class BlockingPort:
    def __init__(self):
        self.first_step_finished = threading.Event()
        self.release_second_step = threading.Event()

    def run_step(self, step):
        if step.step_id == "first":
            self.first_step_finished.set()
            return AdapterResult(success=True, message="first done", data={"command": "cmd1"})
        self.release_second_step.wait(timeout=5)
        return AdapterResult(success=True, message="second done", data={"command": "cmd2"})


class LargeSnapshotPort:
    def run_step(self, step):
        return AdapterResult(
            success=True,
            message="snapshot",
            data={"network_info": {"network_type": "radio-" * 1000}},
        )


class CleanupPort:
    def __init__(self):
        self.started = False
        self.cleaned = False

    def run_step(self, step):
        self.started = True
        return AdapterResult(success=True, message="started")

    def cleanup_open_explicit_sessions(self):
        if not self.started:
            return []
        self.started = False
        self.cleaned = True
        return [AdapterResult(success=True, message="cleaned", data={"session_key": "fake_session"})]


class FailedCleanupPort:
    def run_step(self, step):
        return AdapterResult(success=True, message="started")

    def cleanup_open_explicit_sessions(self):
        return [AdapterResult(success=False, message="cleanup failed", data={"session_key": "bad"})]


class ExceptionCleanupPort:
    def run_step(self, step):
        return AdapterResult(success=True, message="started")

    def cleanup_open_explicit_sessions(self):
        raise RuntimeError("cleanup crashed")


def make_plan(run_id="run-1", adapter="pass"):
    return RunPlan(
        run_id=run_id,
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[StepPlan(step_id="step-1", kind="noop", adapter=adapter)],
            )
        ],
    )


def test_orchestrator_executes_successful_run(tmp_path):
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"pass": PassingPort()},
        run_async=False,
    )

    record = orchestrator.create_run(make_plan())

    assert record.status == Status.PASSED
    assert record.summary["passed"] == 1
    assert (Path(record.artifact_dir) / "run.json").exists()


def test_orchestrator_marks_failed_case(tmp_path):
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"fail": FailingPort()},
        run_async=False,
    )

    record = orchestrator.create_run(make_plan(adapter="fail"))

    assert record.status == Status.FAILED
    assert record.summary["failed"] == 1
    assert record.case_records[0].step_records[0].status == Status.FAILED


def test_orchestrator_treats_non_required_step_failure_as_skipped(tmp_path):
    plan = RunPlan(
        run_id="run-optional",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(step_id="optional", kind="noop", adapter="fail", required=False),
                    StepPlan(step_id="required", kind="noop", adapter="pass"),
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"fail": FailingPort(), "pass": PassingPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)

    assert record.status == Status.PASSED
    assert record.case_records[0].step_records[0].status == Status.SKIPPED
    assert record.case_records[0].step_records[1].status == Status.PASSED


def test_orchestrator_writes_execution_log_for_failed_steps(tmp_path):
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"fail": FailingPort()},
        run_async=False,
    )

    record = orchestrator.create_run(make_plan(adapter="fail"))
    log_path = Path(record.artifact_dir) / "execution.log"
    log_text = log_path.read_text(encoding="utf-8")

    assert log_path.exists()
    assert "run_id=run-1" in log_text
    assert "case=case" in log_text
    assert "step=step-1" in log_text
    assert "status=failed" in log_text
    assert "failed" in log_text


def test_orchestrator_writes_operation_command_and_output_to_execution_log(tmp_path):
    plan = RunPlan(
        run_id="run-command",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(
                        step_id="ssh-1",
                        kind="base_ssh_command_once",
                        adapter="command",
                        action="base_ssh_command_once",
                        parameters={"command": "odi -n duapp0 display-ue-info", "ssh_password": "secret"},
                    )
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"command": CommandPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    step_data = record.case_records[0].step_records[0].data
    log_text = (Path(record.artifact_dir) / "execution.log").read_text(encoding="utf-8")

    assert step_data["operation"] == "base_ssh_command_once"
    assert step_data["command"] == "odi -n duapp0 display-ue-info"
    assert "operation=base_ssh_command_once" in log_text
    assert "command=odi -n duapp0 display-ue-info" in log_text
    assert "stdout=hello" in log_text
    assert "stderr=warn" in log_text
    assert "secret" not in log_text


def test_orchestrator_writes_nested_command_results_to_execution_log(tmp_path):
    plan = RunPlan(
        run_id="run-repeat-log",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(
                        step_id="repeat",
                        kind="base_ssh_command_repeat",
                        adapter="repeat",
                        action="base_ssh_command_repeat",
                        parameters={"command": "wrapper"},
                    )
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"repeat": RepeatResultPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    log_text = (Path(record.artifact_dir) / "execution.log").read_text(encoding="utf-8")

    assert "results=" in log_text
    assert "cmd-1" in log_text
    assert "out-1" in log_text
    assert "cmd-2" in log_text
    assert "err-2" in log_text
    assert "result[1].input=cmd-1" in log_text
    assert "result[1].stdout=out-1" in log_text
    assert "result[2].input=cmd-2" in log_text
    assert "result[2].stderr=err-2" in log_text


def test_orchestrator_routes_capture_and_ssh_logs_to_case_named_timestamp_folder(tmp_path):
    recorder = RecordingPort()
    plan = RunPlan(
        run_id="run-outputs",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="RRC 测试用例",
                step_plans=[
                    StepPlan(
                        step_id="web-stop",
                        kind="base_web_capture_stop",
                        adapter="base_web",
                        action="base_web_capture_stop",
                        parameters={"download_dir": r"D:\old_web"},
                    ),
                    StepPlan(
                        step_id="ssh-start",
                        kind="base_ssh_command_start",
                        adapter="ssh",
                        action="base_ssh_command_start",
                        parameters={"ssh_log_output_dir": r"D:\old_ssh", "command": "date"},
                    ),
                    StepPlan(
                        step_id="device-capture",
                        kind="device_capture",
                        adapter="capture",
                        parameters={"case_dir": r"D:\old_capture"},
                    ),
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"base_web": recorder, "ssh": recorder, "capture": recorder},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    case_dir = Path(record.case_records[0].artifact_dir)

    assert re.fullmatch(r"RRC_测试用例_\d{8}_\d{6}", case_dir.name)
    assert case_dir.parent == Path(record.artifact_dir) / "cases"
    assert recorder.calls[0][1]["download_dir"] == str(case_dir)
    assert recorder.calls[1][1]["ssh_log_output_dir"] == str(case_dir)
    assert recorder.calls[2][1]["case_dir"] == str(case_dir)


def test_async_run_updates_store_after_each_step_for_realtime_ui(tmp_path):
    port = BlockingPort()
    plan = RunPlan(
        run_id="run-realtime",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(step_id="first", kind="noop", adapter="block"),
                    StepPlan(step_id="second", kind="noop", adapter="block"),
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"block": port},
        run_async=True,
    )

    orchestrator.create_run(plan)
    assert port.first_step_finished.wait(timeout=5)
    deadline = time.time() + 5
    live_record = None
    while time.time() < deadline:
        live_record = orchestrator.get_run("run-realtime")
        if live_record and live_record.case_records and live_record.case_records[0].step_records:
            break
        time.sleep(0.05)

    assert live_record is not None
    assert live_record.case_records[0].status == Status.RUNNING
    assert live_record.case_records[0].step_records[0].step_id == "first"
    assert live_record.case_records[0].step_records[0].data["command"] == "cmd1"

    port.release_second_step.set()


def test_async_run_reports_current_running_step_before_it_finishes(tmp_path):
    port = BlockingPort()
    plan = RunPlan(
        run_id="run-current-step",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(step_id="first", kind="noop", adapter="block"),
                    StepPlan(step_id="second", kind="noop", adapter="block"),
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"block": port},
        run_async=True,
    )

    orchestrator.create_run(plan)
    assert port.first_step_finished.wait(timeout=5)
    deadline = time.time() + 5
    live_record = None
    while time.time() < deadline:
        live_record = orchestrator.get_run("run-current-step")
        steps = live_record.case_records[0].step_records if live_record and live_record.case_records else []
        if len(steps) == 2 and steps[1].status == Status.RUNNING:
            break
        time.sleep(0.05)

    assert live_record is not None
    steps = live_record.case_records[0].step_records
    assert steps[0].step_id == "first"
    assert steps[0].status == Status.PASSED
    assert steps[1].step_id == "second"
    assert steps[1].status == Status.RUNNING

    port.release_second_step.set()


def test_orchestrator_externalizes_large_step_payloads(tmp_path):
    plan = RunPlan(
        run_id="run-large",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[StepPlan(step_id="pre_snapshot", kind="snapshot", adapter="snapshot")],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"snapshot": LargeSnapshotPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    case_json = Path(record.case_records[0].artifact_dir) / "case.json"
    case_data = json.loads(case_json.read_text(encoding="utf-8"))
    network_type = case_data["step_records"][0]["data"]["network_info"]["network_type"]

    assert network_type["type"] == "external_payload"
    assert network_type["path"] == "payloads/pre_snapshot/network_info-network_type.txt"
    assert ("radio-" * 1000) not in case_json.read_text(encoding="utf-8")
    payload_path = Path(record.case_records[0].artifact_dir) / network_type["path"]
    assert payload_path.read_text(encoding="utf-8") == "radio-" * 1000


def test_orchestrator_cleans_open_explicit_sessions_without_failing_case(tmp_path):
    cleanup_port = CleanupPort()
    plan = RunPlan(
        run_id="run-cleanup",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[
                    StepPlan(
                        step_id="s1",
                        kind="fake_start",
                        adapter="cleanup",
                        action="fake_start",
                    )
                ],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"cleanup": cleanup_port},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    case_record = record.case_records[0]

    assert record.status == Status.PASSED
    assert case_record.status == Status.PASSED
    assert cleanup_port.cleaned is True
    assert case_record.metadata["warnings"] == ["执行结束会尝试清理"]
    assert case_record.step_records[-1].kind == "cleanup_explicit_sessions"
    assert case_record.step_records[-1].data["warning"] == "执行结束会尝试清理"


def test_orchestrator_marks_failed_cleanup_step_status(tmp_path):
    plan = RunPlan(
        run_id="run-cleanup-fail",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[StepPlan(step_id="s1", kind="fake_start", adapter="cleanup", action="fake_start")],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"cleanup": FailedCleanupPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    cleanup_record = record.case_records[0].step_records[-1]

    assert record.status == Status.FAILED
    assert cleanup_record.status == Status.FAILED
    assert cleanup_record.data["cleanup_success"] is False


def test_orchestrator_marks_cleanup_exception_as_error(tmp_path):
    plan = RunPlan(
        run_id="run-cleanup-error",
        device_id="device-1",
        case_plans=[
            CasePlan(
                case_id="case-1",
                name="case",
                step_plans=[StepPlan(step_id="s1", kind="fake_start", adapter="cleanup", action="fake_start")],
            )
        ],
    )
    orchestrator = RunOrchestrator(
        artifacts_root=tmp_path,
        adapters={"cleanup": ExceptionCleanupPort()},
        run_async=False,
    )

    record = orchestrator.create_run(plan)
    cleanup_record = record.case_records[0].step_records[-1]

    assert record.status == Status.FAILED
    assert cleanup_record.status == Status.ERROR
    assert cleanup_record.data["cleanup_success"] is False
    assert cleanup_record.data["error"] == "cleanup crashed"
