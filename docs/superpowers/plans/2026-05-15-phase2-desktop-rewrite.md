# Phase 2 Desktop Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic Tkinter desktop implementation with a modular desktop package while preserving `desktop_app.py` as the release executable entrypoint.

**Architecture:** Create a `desktop` package with state, controller, formatting, shell, and focused widgets. Widgets depend on the controller and shared state, while controller depends on `PmTestRunManager`, `DeviceManager`, and settings helpers.

**Tech Stack:** Python 3.11, Tkinter/ttk, dataclasses, pytest, existing `pm_tests.PmTestRunManager`, `device.DeviceManager`, and `app_settings`.

---

## File Structure

- Create `desktop/__init__.py`: package marker.
- Create `desktop/state.py`: `CaseDraft`, `DesktopState`, queue operations, status normalization.
- Create `desktop/formatters.py`: run/case/step normalization and display text helpers.
- Create `desktop/controller.py`: desktop service facade around devices, PM runs, and settings.
- Create `desktop/main.py`: new `DesktopApp` shell and widget composition.
- Create `desktop/widgets/__init__.py`: widget package marker.
- Create `desktop/widgets/devices.py`: device and preflight panel.
- Create `desktop/widgets/cases.py`: operation templates and case queue panel.
- Create `desktop/widgets/run_monitor.py`: run controls, history, and timeline panel.
- Create `desktop/widgets/results.py`: detail/JSON inspector panel.
- Create `desktop/widgets/settings.py`: runtime settings panel.
- Replace most of `desktop_app.py` with thin entrypoint that imports `desktop.main.DesktopApp`.
- Add tests: `tests/test_desktop_state.py`, `tests/test_desktop_formatters.py`, `tests/test_desktop_controller.py`, `tests/test_desktop_shell.py`.

## Task 1: Desktop State Model

**Files:**
- Create: `desktop/__init__.py`
- Create: `desktop/state.py`
- Test: `tests/test_desktop_state.py`

- [ ] **Step 1: Write failing state tests**

```python
from desktop.state import CaseDraft, DesktopState, normalize_status


def test_case_draft_converts_to_legacy_case_dict():
    case = CaseDraft(
        name="Ping Case",
        host="10.0.0.1",
        capture_enabled=True,
        ping_enabled=True,
        server_action="base_ssh_output_log",
    )

    assert case.to_legacy_case() == {
        "name": "Ping Case",
        "host": "10.0.0.1",
        "count": 5,
        "capture_enabled": True,
        "ping_enabled": True,
        "server_action": "base_ssh_output_log",
    }


def test_desktop_state_manages_case_queue_and_selection():
    state = DesktopState()
    state.add_case(CaseDraft(name="A", host="1.1.1.1"))
    state.add_case(CaseDraft(name="B", host="2.2.2.2"))

    assert state.selected_case_index == 1
    assert state.selected_case().name == "B"

    state.select_case(0)
    assert state.selected_case().name == "A"

    state.clear_cases()
    assert state.selected_case() is None
    assert state.selected_case_index == -1


def test_normalize_status_prefers_status_then_state():
    assert normalize_status({"status": "passed", "state": "failed"}) == "passed"
    assert normalize_status({"state": "running"}) == "running"
    assert normalize_status({}) == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_state.py -v`

Expected: FAIL because `desktop.state` does not exist.

- [ ] **Step 3: Implement state model**

Implement `CaseDraft`, `DesktopState`, and `normalize_status` exactly as tested. `CaseDraft.count` defaults to 5. `DesktopState.add_case()` selects the newly added case.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_state.py -v`

Expected: PASS.

## Task 2: Desktop Formatters

**Files:**
- Create: `desktop/formatters.py`
- Test: `tests/test_desktop_formatters.py`

- [ ] **Step 1: Write failing formatter tests**

```python
from desktop.formatters import extract_step_rows, format_error, format_run_summary


def test_extract_step_rows_uses_case_records_and_step_records():
    run = {
        "run_id": "run-1",
        "status": "failed",
        "case_records": [
            {
                "name": "case",
                "status": "failed",
                "step_records": [
                    {
                        "step_id": "phone_ping",
                        "kind": "phone_ping",
                        "adapter": "traffic",
                        "status": "failed",
                        "message": "Ping failed",
                        "error": {"code": "PING_FAILED", "adapter": "traffic", "message": "timeout"},
                    }
                ],
            }
        ],
    }

    rows = extract_step_rows(run)

    assert rows == [
        {
            "case": "case",
            "step": "phone_ping",
            "adapter": "traffic",
            "status": "failed",
            "message": "Ping failed",
            "error": "PING_FAILED traffic: timeout",
        }
    ]


def test_format_run_summary_uses_status_and_summary():
    text = format_run_summary({
        "run_id": "run-1",
        "device_id": "device-1",
        "status": "passed",
        "summary": {"passed": 2, "total": 3, "failed": 1},
    })

    assert "run-1" in text
    assert "device-1" in text
    assert "passed" in text
    assert "2/3" in text


def test_format_error_handles_missing_error():
    assert format_error(None) == ""
    assert format_error({"code": "X", "adapter": "adb", "message": "bad"}) == "X adb: bad"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_formatters.py -v`

Expected: FAIL because `desktop.formatters` does not exist.

- [ ] **Step 3: Implement formatters**

Implement `format_error()`, `format_run_summary()`, `extract_step_rows()`, and any private helpers needed. Support both `case_records`/`step_records` and legacy `results`/`steps`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_formatters.py -v`

Expected: PASS.

## Task 3: Desktop Controller

**Files:**
- Create: `desktop/controller.py`
- Test: `tests/test_desktop_controller.py`

- [ ] **Step 1: Write failing controller tests**

```python
from desktop.controller import DesktopController
from desktop.state import CaseDraft


class FakeDeviceManager:
    last_error = ""

    def get_connected_devices(self):
        return ["device-1"]


class FakePmManager:
    def __init__(self):
        self.created = None

    def get_templates(self):
        return [{"template_id": "fixed_ping_only", "name": "Ping", "host": "1.1.1.1"}]

    def inspect_device(self, device_id):
        return {"success": True, "device_id": device_id}

    def create_run(self, device_id, cases):
        self.created = (device_id, cases)
        return {"success": True, "run": {"run_id": "run-1", "device_id": device_id, "status": "queued"}}

    def list_runs(self, limit=20):
        return [{"run_id": "run-1", "status": "queued"}]

    def get_run(self, run_id):
        return {"run_id": run_id, "status": "passed"}

    def request_stop(self, run_id):
        return {"run_id": run_id, "status": "stopping"}


def test_controller_creates_run_from_case_drafts():
    pm = FakePmManager()
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=pm)

    result = controller.create_run("device-1", [CaseDraft(name="case", host="1.1.1.1")])

    assert result["run"]["run_id"] == "run-1"
    assert pm.created[0] == "device-1"
    assert pm.created[1][0]["name"] == "case"


def test_controller_wraps_devices_templates_and_runs():
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=FakePmManager())

    assert controller.refresh_devices() == ["device-1"]
    assert controller.get_templates()[0]["template_id"] == "fixed_ping_only"
    assert controller.inspect_device("device-1")["success"] is True
    assert controller.list_runs()[0]["run_id"] == "run-1"
    assert controller.get_run("run-1")["status"] == "passed"
    assert controller.request_stop("run-1")["status"] == "stopping"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_controller.py -v`

Expected: FAIL because `desktop.controller` does not exist.

- [ ] **Step 3: Implement controller**

Implement `DesktopController` with injectable `device_manager` and `pm_manager`. Default to real `DeviceManager()` and `PmTestRunManager()` when not injected. Include settings methods that delegate to `load_runtime_settings`, `save_runtime_settings`, and `reset_runtime_settings`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_controller.py -v`

Expected: PASS.

## Task 4: Tk Shell And Widgets

**Files:**
- Create: `desktop/widgets/__init__.py`
- Create: `desktop/widgets/devices.py`
- Create: `desktop/widgets/cases.py`
- Create: `desktop/widgets/run_monitor.py`
- Create: `desktop/widgets/results.py`
- Create: `desktop/widgets/settings.py`
- Create: `desktop/main.py`
- Test: `tests/test_desktop_shell.py`

- [ ] **Step 1: Write failing shell smoke test**

```python
import tkinter as tk

from desktop.controller import DesktopController
from desktop.main import DesktopApp


class FakeDeviceManager:
    last_error = ""

    def get_connected_devices(self):
        return ["device-1"]


class FakePmManager:
    def get_templates(self):
        return [{"template_id": "fixed_ping_only", "name": "Ping", "host": "1.1.1.1"}]

    def inspect_device(self, device_id):
        return {"success": True, "device_id": device_id}

    def create_run(self, device_id, cases):
        return {"success": True, "run": {"run_id": "run-1", "device_id": device_id, "status": "queued", "summary": {"passed": 0, "total": 1}}}

    def list_runs(self, limit=20):
        return [{"run_id": "run-1", "device_id": "device-1", "status": "queued", "summary": {"passed": 0, "total": 1}}]

    def get_run(self, run_id):
        return {"run_id": run_id, "device_id": "device-1", "status": "passed", "summary": {"passed": 1, "total": 1}, "case_records": []}

    def request_stop(self, run_id):
        return {"run_id": run_id, "status": "stopping"}


def test_desktop_shell_creates_critical_panels():
    root = tk.Tk()
    root.withdraw()
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=FakePmManager())
    app = DesktopApp(root, controller=controller, start_polling=False)
    root.update_idletasks()

    assert hasattr(app, "devices_panel")
    assert hasattr(app, "cases_panel")
    assert hasattr(app, "run_monitor_panel")
    assert hasattr(app, "results_panel")
    assert hasattr(app, "settings_panel")
    assert app.state.case_queue

    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_desktop_shell.py -v`

Expected: FAIL because `desktop.main` and widget modules do not exist.

- [ ] **Step 3: Implement widget modules and shell**

Implement simple focused Tkinter frames:

- `DevicesPanel`: refresh button, listbox, selected device label, preflight text.
- `CasesPanel`: template list, add case button, queue list.
- `RunMonitorPanel`: start, stop, refresh buttons; run history list; step table.
- `ResultsPanel`: summary text, raw JSON text.
- `SettingsPanel`: raw settings JSON editor with save/reset/reload buttons.
- `DesktopApp`: header, three-column `PanedWindow` or grid layout, shared state, controller, and event wiring.

Keep implementation compact. Use text buttons. Preserve default window size around 1220x860.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_desktop_shell.py -v`

Expected: PASS.

## Task 5: Replace Desktop Entrypoint

**Files:**
- Modify: `desktop_app.py`
- Test: existing tests plus compile smoke.

- [ ] **Step 1: Replace monolithic entrypoint**

Rewrite `desktop_app.py` so it keeps:

- imports for `json`, `logging`, `os`, `Path`, `sys`, and `Any` if needed
- global `tk`, `ttk`, `messagebox`, `scrolledtext`
- `_configure_logging()`
- `_prepare_frozen_gui_environment()`
- `_import_tk_modules()`
- `DesktopApp` import/alias from `desktop.main`
- `main()`

Remove the old monolithic `DesktopApp` class implementation.

- [ ] **Step 2: Run compile smoke**

Run: `python -m py_compile desktop_app.py desktop/main.py desktop/controller.py desktop/state.py`

Expected: no output and exit code 0.

- [ ] **Step 3: Run desktop shell test**

Run: `python -m pytest tests/test_desktop_shell.py -v`

Expected: PASS.

## Task 6: Full Verification

**Files:**
- Modify only files needed by verification failures.

- [ ] **Step 1: Run all tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Run full compile smoke**

Run: `python -m py_compile app.py desktop_app.py desktop/main.py desktop/controller.py desktop/state.py desktop/formatters.py desktop/widgets/devices.py desktop/widgets/cases.py desktop/widgets/run_monitor.py desktop/widgets/results.py desktop/widgets/settings.py`

Expected: no output and exit code 0.

- [ ] **Step 3: Run hidden Tk initialization smoke**

Run:

```powershell
@'
import tkinter as tk
from desktop.main import DesktopApp
root = tk.Tk()
root.withdraw()
app = DesktopApp(root, start_polling=False)
root.update_idletasks()
print("panels=", all(hasattr(app, name) for name in ["devices_panel", "cases_panel", "run_monitor_panel", "results_panel", "settings_panel"]))
root.destroy()
'@ | python -
```

Expected:

```text
panels= True
```

- [ ] **Step 4: Document git limitation**

Because this workspace has no `.git` directory, do not run commit steps. Record changed files and verification output in the final response.
