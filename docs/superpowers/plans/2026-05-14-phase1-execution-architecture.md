# Phase 1 Execution Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated PM execution managers with one typed execution core that supports real adapters and stable run/case/step records.

**Architecture:** Add a new `pm_tests/core` package for typed models, ports, execution, storage, and compatibility planning. Wrap existing ADB, SSH, base Web, capture, traffic, and snapshot helpers behind adapter ports, then expose one `PmTestRunManager` facade for current entrypoints.

**Tech Stack:** Python 3.11-compatible dataclasses, Flask, Tkinter, pytest, existing ADB/Paramiko/requests helpers.

---

## File Structure

- Create `pm_tests/core/models.py`: dataclasses for plans, records, errors, artifacts, status constants, and serialization.
- Create `pm_tests/core/ports.py`: protocol interfaces and normalized adapter result/session types.
- Create `pm_tests/core/runner.py`: `StepRunner`, timeout/error normalization, cleanup result handling.
- Create `pm_tests/core/store.py`: thread-safe `RunStore`.
- Create `pm_tests/core/orchestrator.py`: `RunOrchestrator`, `CaseExecutor`, stop handling, artifact persistence.
- Create `pm_tests/core/planner.py`: convert legacy PM payload/cases into `RunPlan`.
- Create `pm_tests/core/adapters.py`: real adapter wrappers over existing helpers.
- Create `pm_tests/core/facade.py`: compatibility `PmTestRunManager` facade used by Flask and Tkinter.
- Modify `pm_tests/__init__.py`: export the new facade as the active PM service.
- Modify `app.py`: route stop requests if needed and keep PM routes using the facade.
- Modify `desktop_app.py`: keep current calls compatible with the new facade shape.
- Create `tests/test_core_models.py`, `tests/test_step_runner.py`, `tests/test_orchestrator.py`, `tests/test_planner.py`, `tests/test_facade.py`.

## Task 1: Typed Models And Serialization

**Files:**
- Create: `pm_tests/core/__init__.py`
- Create: `pm_tests/core/models.py`
- Test: `tests/test_core_models.py`

- [ ] **Step 1: Write the failing model tests**

```python
# tests/test_core_models.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_core_models.py -v`

Expected: FAIL because `pm_tests.core.models` does not exist.

- [ ] **Step 3: Implement models**

Create `pm_tests/core/__init__.py`:

```python
"""Core PM execution architecture."""
```

Create `pm_tests/core/models.py` with dataclasses for `Status`, `AdapterError`, `Artifact`, `StepPlan`, `CasePlan`, `RunPlan`, `StepRecord`, `CaseRecord`, `RunRecord`, `utc_now_iso`, and `to_serializable`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_core_models.py -v`

Expected: PASS.

## Task 2: Port Protocols And Step Runner

**Files:**
- Create: `pm_tests/core/ports.py`
- Create: `pm_tests/core/runner.py`
- Test: `tests/test_step_runner.py`

- [ ] **Step 1: Write the failing step runner tests**

```python
# tests/test_step_runner.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_step_runner.py -v`

Expected: FAIL because `ports.py` and `runner.py` do not exist.

- [ ] **Step 3: Implement port result and runner**

Implement `AdapterResult`, `CleanupHandle`, `StepPort`, and `StepRunner.run()`. `StepRunner` must set timestamps, normalize missing adapters, convert exceptions into `AdapterError(code="ADAPTER_EXCEPTION")`, and set `passed`/`failed`/`error` status.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_step_runner.py -v`

Expected: PASS.

## Task 3: Run Store, Orchestrator, Case Executor

**Files:**
- Create: `pm_tests/core/store.py`
- Create: `pm_tests/core/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator tests**

```python
# tests/test_orchestrator.py
from pathlib import Path

from pm_tests.core.models import CasePlan, RunPlan, StepPlan, Status
from pm_tests.core.orchestrator import RunOrchestrator
from pm_tests.core.ports import AdapterResult


class PassingPort:
    def run_step(self, step):
        return AdapterResult(success=True, message=f"{step.step_id} ok")


class FailingPort:
    def run_step(self, step):
        return AdapterResult(success=False, message="failed")


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -v`

Expected: FAIL because store and orchestrator do not exist.

- [ ] **Step 3: Implement store and orchestrator**

Implement `RunStore` with `put()`, `get()`, `list()`, `request_stop()`, and deep-copy-safe serialization. Implement `RunOrchestrator.create_run()`, synchronous test mode, background worker mode, artifact writes, case execution, summary calculation, and `get_run()`/`list_runs()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_orchestrator.py -v`

Expected: PASS.

## Task 4: Legacy Payload Planner

**Files:**
- Create: `pm_tests/core/planner.py`
- Test: `tests/test_planner.py`

- [ ] **Step 1: Write failing planner tests**

```python
# tests/test_planner.py
from pm_tests.core.planner import build_run_plan_from_legacy_cases, parse_legacy_case_lines


def test_parse_legacy_case_lines_builds_cases():
    cases = parse_legacy_case_lines(
        "用例1,10.0.0.1,true,server_downlink_iperf,false",
        ping_defaults={"host": "8.8.8.8", "count": 5},
    )

    assert cases[0]["name"] == "用例1"
    assert cases[0]["host"] == "10.0.0.1"
    assert cases[0]["server_action"] == "server_downlink_iperf"
    assert cases[0]["ping_enabled"] is False


def test_build_run_plan_creates_step_sequence():
    plan = build_run_plan_from_legacy_cases(
        device_id="device-1",
        cases=[
            {
                "name": "case",
                "host": "10.0.0.1",
                "count": 5,
                "capture_enabled": True,
                "ping_enabled": True,
                "server_action": "base_ssh_output_log,phone_uplink_iperf",
            }
        ],
        settings_snapshot={"ping": {"host": "10.0.0.1", "count": 5}},
    )

    step_ids = [step.step_id for step in plan.case_plans[0].step_plans]
    assert "pre_snapshot" in step_ids
    assert "base_ssh_output_log" in step_ids
    assert "phone_uplink_iperf" in step_ids
    assert "device_capture" in step_ids
    assert "phone_ping" in step_ids
    assert "post_snapshot" in step_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_planner.py -v`

Expected: FAIL because planner does not exist.

- [ ] **Step 3: Implement planner**

Implement `parse_legacy_case_lines()` and `build_run_plan_from_legacy_cases()`. Preserve existing legacy behavior for default host/count and boolean parsing. Create explicit step plans for snapshots, base Web actions, SSH actions, traffic server actions, phone traffic actions, capture, and ping.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_planner.py -v`

Expected: PASS.

## Task 5: Real Adapter Wrappers

**Files:**
- Create: `pm_tests/core/adapters.py`
- Test: `tests/test_adapters_smoke.py`

- [ ] **Step 1: Write adapter smoke tests with monkeypatching**

```python
# tests/test_adapters_smoke.py
from pm_tests.core.adapters import SnapshotAdapter, TrafficAdapter
from pm_tests.core.models import StepPlan


def test_traffic_adapter_ping_uses_device_ping(monkeypatch):
    calls = {}

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls["device_id"] = device_id

        def ping_test(self, host, count):
            calls["host"] = host
            calls["count"] = count
            return {"success": True, "success_count": count, "packet_loss": 0}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)

    result = TrafficAdapter("device-1").run_step(
        StepPlan(
            step_id="phone_ping",
            kind="phone_ping",
            adapter="traffic",
            parameters={"host": "10.0.0.1", "count": 5},
        )
    )

    assert result.success is True
    assert calls == {"device_id": "device-1", "host": "10.0.0.1", "count": 5}


def test_snapshot_adapter_returns_data(monkeypatch):
    class FakeMonitor:
        def __init__(self, device_id):
            pass

        def get_network_info(self):
            return {"success": True, "network": "5G"}

    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeMonitor)

    result = SnapshotAdapter("device-1").run_step(
        StepPlan(step_id="pre_snapshot", kind="snapshot", adapter="snapshot")
    )

    assert result.success is True
    assert result.data["network_info"]["network"] == "5G"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_adapters_smoke.py -v`

Expected: FAIL because adapters do not exist.

- [ ] **Step 3: Implement real adapter wrappers**

Implement wrappers that translate known `StepPlan.kind` values into existing helper calls. Return `AdapterResult` consistently. Keep the first implementation thin and avoid rewriting existing ADB, SSH, Web, capture, or iperf internals unless needed for normalization.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_adapters_smoke.py -v`

Expected: PASS.

## Task 6: Facade And Entry Integration

**Files:**
- Create: `pm_tests/core/facade.py`
- Modify: `pm_tests/__init__.py`
- Modify: `app.py`
- Modify: `desktop_app.py`
- Test: `tests/test_facade.py`

- [ ] **Step 1: Write facade tests**

```python
# tests/test_facade.py
from pm_tests.core.facade import PmTestRunManager


def test_facade_creates_and_lists_runs(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    run = manager.create_run(
        "device-1",
        cases=[{"name": "case", "host": "10.0.0.1", "count": 1, "ping_enabled": False}],
    )

    assert run["success"] is True
    assert run["run"]["device_id"] == "device-1"
    assert manager.get_run(run["run"]["run_id"])["run_id"] == run["run"]["run_id"]
    assert manager.list_runs(limit=1)[0]["run_id"] == run["run"]["run_id"]


def test_facade_templates_are_available(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    templates = manager.get_templates()

    assert templates
    assert templates[0]["template_id"] == "fixed_ping_only"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_facade.py -v`

Expected: FAIL because facade does not exist.

- [ ] **Step 3: Implement facade and exports**

Implement `PmTestRunManager` facade with `get_templates()`, `inspect_device()`, `create_run()`, `request_stop()`, `get_run()`, and `list_runs()`. Export this facade from `pm_tests/__init__.py`. Keep Flask route response shapes compatible where practical by returning dictionaries.

- [ ] **Step 4: Update entrypoints**

Update `app.py` and `desktop_app.py` imports to use the new exported facade. Adjust `app.py:create_pm_run()` if the facade returns `{"success": True, "run": ...}`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_facade.py -v`

Expected: PASS.

## Task 7: Full Verification

**Files:**
- Modify only files needed by failures found during verification.

- [ ] **Step 1: Run all unit tests**

Run: `pytest -v`

Expected: PASS.

- [ ] **Step 2: Run import smoke checks**

Run: `python -m py_compile app.py desktop_app.py pm_tests/core/models.py pm_tests/core/runner.py pm_tests/core/orchestrator.py pm_tests/core/planner.py pm_tests/core/adapters.py pm_tests/core/facade.py`

Expected: no output and exit code 0.

- [ ] **Step 3: Run Flask route smoke if dependencies are available**

Run: `python -c "from app import app; c=app.test_client(); r=c.get('/api/pm/templates'); print(r.status_code); print(r.get_json()['success'])"`

Expected:

```text
200
True
```

- [ ] **Step 4: Document git limitation**

Because this workspace has no `.git` directory, do not run commit steps. Record final changed files and verification output in the final response.
