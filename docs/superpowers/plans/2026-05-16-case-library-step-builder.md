# Case Library Step Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a desktop case library where users create named cases from explicit ordered start/stop steps, save each case to `cases/*.json`, run selected cases, and see command/output/progress in one large console.

**Architecture:** Add a small desktop case-library layer for JSON persistence and step templates, then make PM planning accept explicit `steps` as the primary case input while keeping legacy case dictionaries only as a compatibility path. The Tk UI replaces the visible fixed template list with a scrollable case library, vertical step builder, editable parameters, and a large run console; adapters map each explicit action to existing ADB/SSH/Web behavior with user-controlled stop steps and end-of-case cleanup warnings.

**Tech Stack:** Python 3.11, Tkinter/ttk, pytest, PyInstaller, existing `pm_tests.core` runner/adapters, no Flask, no Appium.

---

## File Structure

- Create: `desktop/case_models.py`
  - Owns `SavedCase`, `CaseStep`, validation helpers, and JSON serialization for schema version 1.
- Create: `desktop/case_templates.py`
  - Owns canonical action IDs, labels, parameter field metadata, and built-in new-format case templates copied from runtime settings.
- Create: `desktop/case_library.py`
  - Owns `cases/*.json` create, load, save, rename, copy, delete, and safe file names.
- Modify: `desktop/state.py`
  - Replaces queue storage from legacy `CaseDraft`-only assumptions to saved case dictionaries while preserving `to_legacy_case()` compatibility for old tests.
- Modify: `desktop/controller.py`
  - Adds case-library methods and passes explicit saved cases into `PmTestRunManager.create_run()`.
- Modify: `desktop/widgets/cases.py`
  - Replaces fixed template list with a scrollable case list, step builder, ordering controls, and parameter editor.
- Modify: `desktop/widgets/results.py`
  - Makes the run console the primary large output area and formats chronological step command/output/progress lines.
- Modify: `desktop/main.py` and `desktop_app.py`
  - Wires new widgets without changing the source/exe entrypoint contract.
- Create: `pm_tests/core/actions.py`
  - Defines canonical action IDs and maps them to adapter/kind/session metadata.
- Modify: `pm_tests/core/models.py`
  - Adds optional `label` and `action` fields to `StepPlan` and preserves them in `StepRecord.data`.
- Modify: `pm_tests/core/planner.py`
  - Converts explicit `steps` to `StepPlan` in exact order; legacy planning remains as fallback.
- Modify: `pm_tests/core/adapters.py`
  - Adds explicit start/stop handling and session lookup for base Web capture, base SSH log, traffic server, and phone actions.
- Modify: `pm_tests/core/facade.py`
  - Exposes new case templates and accepts saved case dicts in `create_run()`.
- Modify: `build.spec`
  - Includes `cases/` sample/default case files only if needed; does not re-add Flask/templates.
- Create/Modify Tests:
  - `tests/test_case_models.py`
  - `tests/test_case_templates.py`
  - `tests/test_case_library.py`
  - `tests/test_planner.py`
  - `tests/test_adapters_smoke.py`
  - `tests/test_desktop_controller.py`
  - `tests/test_desktop_shell.py`
  - `tests/test_desktop_formatters.py`
  - `tests/test_phase6_release_files.py`

## Implementation Tasks

### Task 1: Case Models

**Files:**
- Create: `desktop/case_models.py`
- Test: `tests/test_case_models.py`

- [ ] **Step 1: Write failing serialization and validation tests**

Add this test content:

```python
from desktop.case_models import CaseStep, SavedCase, validate_case


def test_saved_case_round_trips_schema_v1():
    case = SavedCase.new(
        name="test1",
        steps=[
            CaseStep.new(
                action="base_web_capture_start",
                label="基站 Web-开始抓包",
                params={
                    "capture_signal_enabled": True,
                    "capture_data_enabled": False,
                    "capture_fapi_interface": "FAPI1",
                },
            )
        ],
    )

    data = case.to_dict()
    loaded = SavedCase.from_dict(data)

    assert data["schema_version"] == 1
    assert loaded.name == "test1"
    assert loaded.steps[0].action == "base_web_capture_start"
    assert loaded.steps[0].enabled is True


def test_validate_case_requires_name_and_enabled_step():
    empty_name = SavedCase.new(name=" ", steps=[CaseStep.new("phone_ping", "手机-ping", {})])
    no_enabled_steps = SavedCase.new(
        name="test1",
        steps=[CaseStep.new("phone_ping", "手机-ping", {}, enabled=False)],
    )

    assert "用例名称不能为空" in validate_case(empty_name).errors
    assert "至少需要一个启用步骤" in validate_case(no_enabled_steps).errors
```

- [ ] **Step 2: Run the model tests and confirm the expected import failure**

Run: `python -m pytest tests\test_case_models.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'desktop.case_models'`.

- [ ] **Step 3: Implement case dataclasses and validation**

Create `desktop/case_models.py` with these public APIs:

```python
"""Saved desktop case models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(slots=True)
class CaseStep:
    step_id: str
    action: str
    label: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, action: str, label: str, params: dict[str, Any], *, enabled: bool = True) -> "CaseStep":
        return cls(step_id=f"step_{uuid4().hex[:8]}", action=action, label=label, enabled=enabled, params=dict(params))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseStep":
        return cls(
            step_id=str(data.get("step_id") or f"step_{uuid4().hex[:8]}"),
            action=str(data.get("action") or ""),
            label=str(data.get("label") or data.get("action") or "step"),
            enabled=bool(data.get("enabled", True)),
            params=dict(data.get("params") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "label": self.label,
            "enabled": self.enabled,
            "params": dict(self.params),
        }


@dataclass(slots=True)
class SavedCase:
    schema_version: int
    case_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    steps: list[CaseStep] = field(default_factory=list)

    @classmethod
    def new(cls, name: str, steps: list[CaseStep], description: str = "") -> "SavedCase":
        stamp = now_iso()
        return cls(SCHEMA_VERSION, f"case_{uuid4().hex[:8]}", name, description, stamp, stamp, list(steps))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedCase":
        return cls(
            schema_version=int(data.get("schema_version") or SCHEMA_VERSION),
            case_id=str(data.get("case_id") or f"case_{uuid4().hex[:8]}"),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
            steps=[CaseStep.from_dict(item) for item in data.get("steps") or []],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.to_dict() for step in self.steps],
        }


def validate_case(case: SavedCase) -> ValidationResult:
    result = ValidationResult()
    if not case.name.strip():
        result.errors.append("用例名称不能为空")
    if not any(step.enabled for step in case.steps):
        result.errors.append("至少需要一个启用步骤")
    starts = [step.action for step in case.steps if step.enabled and step.action.endswith("_start")]
    stops = [step.action for step in case.steps if step.enabled and step.action.endswith("_stop")]
    if starts and not stops:
        result.warnings.append("存在开始步骤但没有停止步骤，执行结束会尝试清理")
    return result
```

- [ ] **Step 4: Verify model tests pass**

Run: `python -m pytest tests\test_case_models.py -v`

Expected: PASS with 2 tests.

- [ ] **Step 5: Commit or record no-git status**

Run: `git status`

Expected in this workspace: if output says `not a git repository`, skip commit and keep validation output in the final handoff. If git is initialized, run:

```bash
git add desktop/case_models.py tests/test_case_models.py
git commit -m "feat: add saved case model"
```

### Task 2: Step Templates and New Case Templates

**Files:**
- Create: `desktop/case_templates.py`
- Test: `tests/test_case_templates.py`

- [ ] **Step 1: Write failing tests for canonical actions and runtime default copying**

Add:

```python
from desktop.case_templates import ACTIONS, build_default_case_templates, step_from_template


def test_actions_include_base_web_ssh_server_and_phone_options():
    ids = {item.action for item in ACTIONS}

    assert "base_web_capture_start" in ids
    assert "base_web_capture_stop" in ids
    assert "base_ssh_log_start" in ids
    assert "traffic_server_downlink_start" in ids
    assert "traffic_server_downlink_stop" in ids
    assert "phone_uplink_iperf_start" in ids
    assert "phone_uplink_iperf_stop" in ids


def test_step_copies_runtime_defaults_without_mutating_settings():
    settings = {
        "base_url": "http://192.168.13.236:8400",
        "base_username": "root",
        "base_password": "5GNR@root",
        "traffic_server_host": "10.88.149.164",
        "traffic_server_user": "root",
        "traffic_server_password": "Root@164_",
        "iperf_port": 7011,
        "iperf_bandwidth": "100M",
        "iperf_duration": 60,
        "download_dir": "D:\\test\\autopm_system\\log",
    }

    step = step_from_template("traffic_server_downlink_start", settings)
    step.params["server_host"] = "1.1.1.1"

    assert step.params["server_host"] == "1.1.1.1"
    assert settings["traffic_server_host"] == "10.88.149.164"


def test_builtin_case_templates_use_explicit_start_stop_order():
    templates = build_default_case_templates({"traffic_server_host": "10.88.149.164"})
    downlink = next(item for item in templates if item.name == "下行灌包")

    assert [step.action for step in downlink.steps] == [
        "base_web_capture_start",
        "phone_downlink_receive_start",
        "traffic_server_downlink_start",
        "traffic_server_downlink_stop",
        "phone_downlink_receive_stop",
        "base_web_capture_stop",
    ]
```

- [ ] **Step 2: Run template tests and confirm failure**

Run: `python -m pytest tests\test_case_templates.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'desktop.case_templates'`.

- [ ] **Step 3: Implement action metadata, parameter defaults, and built-in templates**

Create `desktop/case_templates.py` with `ActionTemplate(action, label, group, fields, defaults)`, `ACTIONS`, `ACTION_BY_ID`, `step_from_template(action, settings)`, and `build_default_case_templates(settings)`.

Required action IDs:

```python
CANONICAL_ACTIONS = [
    "base_web_capture_start",
    "base_web_capture_stop",
    "base_web_collect_log",
    "base_ssh_log_start",
    "base_ssh_log_stop",
    "traffic_server_downlink_start",
    "traffic_server_downlink_stop",
    "traffic_server_down_ping_start",
    "traffic_server_down_ping_stop",
    "traffic_server_uplink_receive_start",
    "traffic_server_uplink_receive_stop",
    "phone_downlink_receive_start",
    "phone_downlink_receive_stop",
    "phone_uplink_iperf_start",
    "phone_uplink_iperf_stop",
    "phone_ping",
]
```

Default params must copy values from runtime settings:

```python
{
    "base_url": settings.get("base_url", "http://192.168.13.236:8400"),
    "base_username": settings.get("base_username", "root"),
    "base_password": settings.get("base_password", "5GNR@root"),
    "server_host": settings.get("traffic_server_host", "10.88.149.164"),
    "server_user": settings.get("traffic_server_user", "root"),
    "server_password": settings.get("traffic_server_password", "Root@164_"),
    "iperf_port": int(settings.get("iperf_port", 7011)),
    "iperf_bandwidth": settings.get("iperf_bandwidth", "100M"),
    "iperf_duration": int(settings.get("iperf_duration", 60)),
    "capture_signal_enabled": True,
    "capture_data_enabled": False,
    "capture_fapi_interface": "FAPI1",
}
```

- [ ] **Step 4: Verify template tests pass**

Run: `python -m pytest tests\test_case_templates.py -v`

Expected: PASS with 3 tests.

### Task 3: Case Library Persistence

**Files:**
- Create: `desktop/case_library.py`
- Test: `tests/test_case_library.py`

- [ ] **Step 1: Write failing persistence tests**

Add:

```python
from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase


def test_case_library_create_load_rename_copy_delete(tmp_path):
    library = CaseLibrary(tmp_path)
    case = SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {"count": 3})])

    path = library.save(case)
    loaded = library.load(path.name)
    renamed = library.rename(loaded.case_id, "renamed")
    copied = library.copy_case(renamed.case_id, "copy1")
    library.delete(renamed.case_id)

    assert path.exists()
    assert loaded.name == "test1"
    assert renamed.name == "renamed"
    assert copied.name == "copy1"
    assert [item.name for item in library.list_cases()] == ["copy1"]


def test_duplicate_visible_names_have_distinct_files(tmp_path):
    library = CaseLibrary(tmp_path)

    first = library.save(SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {})]))
    second = library.save(SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {})]))

    assert first.name != second.name
    assert len(library.list_cases()) == 2
```

- [ ] **Step 2: Run persistence tests and confirm failure**

Run: `python -m pytest tests\test_case_library.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'desktop.case_library'`.

- [ ] **Step 3: Implement JSON file library**

Create `CaseLibrary(root: Path | str = "cases")` with:

```python
class CaseLibrary:
    def __init__(self, root: Path | str = "cases") -> None: ...
    def list_cases(self) -> list[SavedCase]: ...
    def save(self, case: SavedCase) -> Path: ...
    def load(self, filename_or_case_id: str) -> SavedCase: ...
    def rename(self, case_id: str, name: str) -> SavedCase: ...
    def copy_case(self, case_id: str, name: str) -> SavedCase: ...
    def delete(self, case_id: str) -> None: ...
```

Use UTF-8 JSON, `ensure_ascii=False`, and safe filenames shaped like `<safe-name>-<case_id>.json`. If a file name changes during rename, delete only the old file after the new file is written successfully.

- [ ] **Step 4: Verify persistence tests pass**

Run: `python -m pytest tests\test_case_library.py -v`

Expected: PASS with 2 tests.

### Task 4: Planner Explicit Steps

**Files:**
- Create: `pm_tests/core/actions.py`
- Modify: `pm_tests/core/models.py`
- Modify: `pm_tests/core/planner.py`
- Test: `tests/test_planner.py`
- Test: `tests/test_core_models.py`

- [ ] **Step 1: Add failing planner test for explicit step order**

Append to `tests/test_planner.py`:

```python
from pm_tests.core.planner import build_run_plan


def test_planner_preserves_explicit_case_step_order():
    plan = build_run_plan(
        "device-1",
        [
            {
                "case_id": "case_test1",
                "name": "test1",
                "steps": [
                    {"step_id": "s1", "action": "base_web_capture_start", "label": "抓包开始", "enabled": True, "params": {"capture_fapi_interface": "FAPI3"}},
                    {"step_id": "s2", "action": "phone_ping", "label": "手机 ping", "enabled": False, "params": {"count": 3}},
                    {"step_id": "s3", "action": "base_web_capture_stop", "label": "抓包停止", "enabled": True, "params": {}},
                ],
            }
        ],
    )

    case = plan.case_plans[0]
    assert case.case_id == "case_test1"
    assert [step.action for step in case.step_plans] == ["base_web_capture_start", "base_web_capture_stop"]
    assert [step.step_id for step in case.step_plans] == ["s1", "s3"]
    assert case.step_plans[0].parameters["capture_fapi_interface"] == "FAPI3"
```

- [ ] **Step 2: Run planner test and confirm failure**

Run: `python -m pytest tests\test_planner.py::test_planner_preserves_explicit_case_step_order -v`

Expected: FAIL because `StepPlan` has no `action` attribute or planner ignores explicit `steps`.

- [ ] **Step 3: Implement canonical action mapping**

Create `pm_tests/core/actions.py` with `ActionSpec(action, kind, adapter, session_key, start_action, stop_action)` and a `resolve_action(action: str) -> ActionSpec` function. Map all canonical IDs to existing adapter names: `base_web`, `base_ssh`, `traffic_server`, `android_device`, and preserve legacy `kind` values where existing adapters already expect them.

- [ ] **Step 4: Extend `StepPlan` and planner conversion**

Modify `pm_tests/core/models.py`:

```python
@dataclass(slots=True)
class StepPlan:
    step_id: str
    kind: str
    adapter: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None
    required: bool = True
    action: str = ""
    label: str = ""
```

Modify `pm_tests/core/planner.py` so that when a case dictionary has `steps`, it uses only enabled steps, resolves each action with `resolve_action()`, and creates `StepPlan(..., action=step["action"], label=step["label"])` in user order. Keep the existing legacy branch for dictionaries without `steps`.

- [ ] **Step 5: Verify planner and model tests**

Run: `python -m pytest tests\test_planner.py tests\test_core_models.py -v`

Expected: PASS.

### Task 5: Adapter Explicit Start/Stop Sessions

**Files:**
- Modify: `pm_tests/core/adapters.py`
- Modify: `pm_tests/core/runner.py` or current step runner file if session state is held there
- Test: `tests/test_adapters_smoke.py`
- Test: `tests/test_step_runner.py`

- [ ] **Step 1: Add failing smoke tests for explicit start/stop actions**

Append to `tests/test_adapters_smoke.py`:

```python
from pm_tests.core.adapters import AdapterRegistry
from pm_tests.core.models import StepPlan


def test_registry_accepts_explicit_base_web_capture_actions():
    registry = AdapterRegistry()
    start = StepPlan("s1", "base_web_capture_start", "base_web", action="base_web_capture_start", label="抓包开始")
    stop = StepPlan("s2", "base_web_capture_stop", "base_web", action="base_web_capture_stop", label="抓包停止")

    assert registry.get(start.adapter).can_handle(start)
    assert registry.get(stop.adapter).can_handle(stop)


def test_registry_accepts_explicit_traffic_server_stop_actions():
    registry = AdapterRegistry()
    stop = StepPlan("s1", "traffic_server_downlink_stop", "traffic_server", action="traffic_server_downlink_stop", label="停止下行灌包")

    assert registry.get(stop.adapter).can_handle(stop)
```

- [ ] **Step 2: Run adapter smoke tests and confirm failure**

Run: `python -m pytest tests\test_adapters_smoke.py -v`

Expected: FAIL for unsupported explicit kinds or missing `action` handling.

- [ ] **Step 3: Implement explicit action handling**

In each relevant adapter, treat `step.action or step.kind` as the operation key. Add start/stop handling:

```python
operation = step.action or step.kind
if operation == "traffic_server_downlink_start":
    return self._start_downlink(step)
if operation == "traffic_server_downlink_stop":
    return self._stop_session("traffic_server_downlink")
```

Store long-running session references in the existing run/case context if available. If there is no context object today, add a small `sessions: dict[str, Any]` to the runner execution context and pass it into adapters through the existing adapter call path.

- [ ] **Step 4: Add cleanup warning behavior**

Add a test in `tests/test_step_runner.py` using a case with `base_web_capture_start` and no stop step. Assert that the final case or run metadata contains a warning string containing `执行结束会尝试清理` and that cleanup attempts are included in the step/run data.

- [ ] **Step 5: Verify adapter and runner tests**

Run: `python -m pytest tests\test_adapters_smoke.py tests\test_step_runner.py -v`

Expected: PASS.

### Task 6: Desktop Controller Case Library API

**Files:**
- Modify: `desktop/controller.py`
- Modify: `desktop/state.py`
- Modify: `pm_tests/core/facade.py`
- Test: `tests/test_desktop_controller.py`
- Test: `tests/test_facade.py`

- [ ] **Step 1: Add failing controller tests**

Append to `tests/test_desktop_controller.py`:

```python
from desktop.controller import DesktopController


def test_controller_exposes_case_library_operations(tmp_path):
    controller = DesktopController()
    controller.case_library.root = tmp_path

    case = controller.create_case_from_template("下行灌包", {"traffic_server_host": "10.88.149.164"})
    controller.rename_case(case.case_id, "test1")
    cases = controller.list_saved_cases()

    assert cases[0].name == "test1"
    assert cases[0].steps[0].action == "base_web_capture_start"
```

- [ ] **Step 2: Run controller test and confirm failure**

Run: `python -m pytest tests\test_desktop_controller.py::test_controller_exposes_case_library_operations -v`

Expected: FAIL because controller has no `case_library` and no case-library methods.

- [ ] **Step 3: Implement controller methods**

Add to `DesktopController.__init__`:

```python
from desktop.case_library import CaseLibrary

self.case_library = CaseLibrary()
```

Add methods:

```python
def list_saved_cases(self): ...
def create_blank_case(self, name: str, settings: dict): ...
def create_case_from_template(self, template_name: str, settings: dict): ...
def save_case(self, case): ...
def rename_case(self, case_id: str, name: str): ...
def copy_case(self, case_id: str, name: str): ...
def delete_case(self, case_id: str): ...
def get_step_templates(self) -> list[dict]: ...
```

Update `create_run()` so saved `SavedCase` objects and saved case dicts are passed as dictionaries with `steps`, while old `CaseDraft` objects still use `to_legacy_case()`.

- [ ] **Step 4: Update facade templates**

Change `PmTestRunManager.get_templates()` to return the new case templates from `desktop.case_templates` or a core-safe equivalent. The desktop UI must not display the old fixed template list.

- [ ] **Step 5: Verify controller and facade tests**

Run: `python -m pytest tests\test_desktop_controller.py tests\test_facade.py -v`

Expected: PASS.

### Task 7: Tk Case Library and Step Builder UI

**Files:**
- Modify: `desktop/widgets/cases.py`
- Modify: `desktop/main.py`
- Modify: `desktop_app.py`
- Test: `tests/test_desktop_shell.py`

- [ ] **Step 1: Add failing Tk shell test for visible controls and scrollability**

Append to `tests/test_desktop_shell.py`:

```python
def test_cases_panel_has_scrollable_case_library_and_step_builder(tk_root):
    from desktop.main import DesktopApp

    app = DesktopApp(tk_root)
    tk_root.update_idletasks()

    panel = app.cases_panel
    assert hasattr(panel, "case_list")
    assert hasattr(panel, "step_list")
    assert hasattr(panel, "step_params_frame")
    assert hasattr(panel, "scroll_canvas")
    assert "基站 Web" in panel.available_group_names()
    assert "基站 SSH" in panel.available_group_names()
    assert "灌包服务器" in panel.available_group_names()
    assert "手机" in panel.available_group_names()
```

- [ ] **Step 2: Run shell test and confirm failure**

Run: `python -m pytest tests\test_desktop_shell.py::test_cases_panel_has_scrollable_case_library_and_step_builder -v`

Expected: FAIL because the current `CasesPanel` only has fixed templates and queue widgets.

- [ ] **Step 3: Replace fixed template list with scrollable layout**

In `desktop/widgets/cases.py`, rebuild `CasesPanel` with three visible columns or stacked sections that fit the current desktop window:

```text
left:   用例库 list + 新建/复制/重命名/删除/加入队列
middle: 步骤 list + 添加/删除/上移/下移/启用
right:  步骤参数 editor + 保存
bottom: 用例队列
```

Use a `Canvas` + vertical scrollbar as the outer container. Keep attributes `scroll_canvas`, `case_list`, `step_list`, `step_params_frame`, and `queue_list` for tests and maintenance checks. Do not add a Web page or `templates/index.html`.

- [ ] **Step 4: Implement step controls**

Wire these user actions to controller/library methods:

```python
create_blank_case()
create_case_from_template()
copy_selected_case()
rename_selected_case()
delete_selected_case()
add_step(action_id)
delete_selected_step()
move_step_up()
move_step_down()
toggle_step_enabled()
save_selected_case()
add_selected_case_to_queue()
```

Parameter widgets must include fields for IP/host, port, bandwidth, duration, packet length, capture signal/data checkboxes, and FAPI combobox with `FAPI1` and `FAPI3`.

- [ ] **Step 5: Verify Tk shell tests**

Run: `python -m pytest tests\test_desktop_shell.py -v`

Expected: PASS.

### Task 8: Run Console Formatting

**Files:**
- Modify: `desktop/widgets/results.py`
- Modify: `desktop/formatters.py` if current formatter module owns result text
- Test: `tests/test_desktop_formatters.py`

- [ ] **Step 1: Add failing formatter test**

Append:

```python
from desktop.formatters import format_run_console


def test_format_run_console_shows_progress_command_output_and_artifacts():
    run = {
        "case_records": [
            {
                "name": "test1",
                "step_records": [
                    {
                        "step_id": "s1",
                        "kind": "base_web_capture_start",
                        "adapter": "base_web",
                        "status": "passed",
                        "message": "started",
                        "data": {
                            "label": "基站 Web-开始抓包",
                            "command": "web capture CP FAPI1",
                            "return_preview": "started",
                        },
                        "artifacts": [{"kind": "pcap", "path": "D:\\test\\autopm_system\\log\\a.pcap"}],
                    }
                ],
            }
        ],
    }

    text = format_run_console(run)

    assert "[1/1] test1 - 基站 Web-开始抓包" in text
    assert "命令: web capture CP FAPI1" in text
    assert "返回: started" in text
    assert "产物: D:\\test\\autopm_system\\log\\a.pcap" in text
```

- [ ] **Step 2: Run formatter test and confirm failure**

Run: `python -m pytest tests\test_desktop_formatters.py::test_format_run_console_shows_progress_command_output_and_artifacts -v`

Expected: FAIL because `format_run_console` does not exist or does not render these lines.

- [ ] **Step 3: Implement run console formatter**

Add `format_run_console(run: dict) -> str` that iterates cases and steps chronologically, calculates `[current/total]`, and prints label, status, command, return preview, warnings, and artifact paths. Update `ResultsPanel` to make this text area the largest primary result view.

- [ ] **Step 4: Verify formatter tests**

Run: `python -m pytest tests\test_desktop_formatters.py -v`

Expected: PASS.

### Task 9: Remove Visible Old Templates and Protect Release Contract

**Files:**
- Modify: `tests/test_phase6_release_files.py`
- Modify: `build.spec` only if package data must include seeded case files
- Verify: `release\MobileTestPlatform\MobileTestPlatform.exe`

- [ ] **Step 1: Add regression tests for no Flask/Web/Appium reintroduction**

Add assertions:

```python
from pathlib import Path


def test_no_flask_or_web_templates_are_packaged():
    assert not Path("templates").exists()
    assert "Flask" not in Path("requirements.txt").read_text(encoding="utf-8")
    assert "templates" not in Path("build.spec").read_text(encoding="utf-8")


def test_no_appium_imports_in_execution_path():
    execution_files = [
        Path("desktop/controller.py"),
        Path("pm_tests/core/planner.py"),
        Path("pm_tests/core/adapters.py"),
        Path("pm_tests/core/facade.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in execution_files)
    assert "appium" not in combined.lower()
```

- [ ] **Step 2: Run release-file regression tests**

Run: `python -m pytest tests\test_phase6_release_files.py -v`

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run: `$env:PYTHONPATH='.'; python -m pytest -v`

Expected: all tests pass. The last known baseline before this plan was 39 passed; the new total should be higher after adding case tests.

- [ ] **Step 4: Verify Tk initialization at source level**

Run the Tk verification from `UI_MODIFICATION_NOTES.md`:

```powershell
python -m py_compile desktop_app.py
@'
import desktop_app
desktop_app._import_tk_modules()
tk = desktop_app.tk
root = tk.Tk()
root.withdraw()
app = desktop_app.DesktopApp(root)
root.update_idletasks()
print('has_cases_panel=', hasattr(app, 'cases_panel'))
print('has_scroll=', hasattr(app.cases_panel, 'scroll_canvas'))
print('groups=', app.cases_panel.available_group_names())
root.destroy()
'@ | python -
```

Expected output includes:

```text
has_cases_panel= True
has_scroll= True
groups= ['基站 Web', '基站 SSH', '灌包服务器', '手机']
```

- [ ] **Step 5: Rebuild default release path**

Run:

```powershell
$targets = @('build_release','release\MobileTestPlatform')
foreach ($t in $targets) {
    if (Test-Path $t) {
        Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction Stop
    }
}
python -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release
```

Expected: `release\MobileTestPlatform\MobileTestPlatform.exe` exists.

- [ ] **Step 6: Start exe for smoke validation if approval allows GUI execution**

Run:

```powershell
$proc = Start-Process -FilePath 'D:\test\mobile_automation_platform\release\MobileTestPlatform\MobileTestPlatform.exe' -WorkingDirectory 'D:\test\mobile_automation_platform\release\MobileTestPlatform' -PassThru
Start-Sleep -Seconds 8
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
```

Expected: process starts without immediate crash. If GUI execution is blocked by tool approval, record that blocker and the exact command.

## Self-Review

- Spec coverage: local `cases/*.json` persistence is covered by Tasks 1-3; explicit start/stop actions and ordering are covered by Tasks 2, 4, and 5; desktop UI replacement and scrollability are covered by Task 7; run console is covered by Task 8; release and no Flask/Appium regression are covered by Task 9.
- Red-flag scan: this plan uses concrete paths, action IDs, commands, and expected outputs. It does not require external API, database storage, Flask UI, or Appium.
- Type consistency: `CaseStep.action`, `SavedCase.steps`, `StepPlan.action`, and `format_run_console(run)` are used consistently across model, planner, adapters, controller, UI, and tests.
