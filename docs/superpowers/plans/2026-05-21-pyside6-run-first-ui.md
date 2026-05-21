# PySide6 Run-First UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6 desktop UI that opens directly to the run workflow and makes device, case, configuration readiness, start, live execution, and logs clear.

**Architecture:** Add a new `desktop_qt` package that reuses the existing `DesktopController`, case library, settings persistence, and PM execution manager. Keep the current Tkinter `desktop` package in place until the Qt app is covered by smoke tests, then switch `desktop_app.py` to launch PySide6 by default.

**Tech Stack:** Python, PySide6, pytest, existing `desktop` business modules, existing `pm_tests` execution core.

---

## File Structure

- Modify: `requirements.txt` to add `PySide6`.
- Create: `desktop_qt/__init__.py` for package metadata.
- Create: `desktop_qt/preflight.py` for selected-case readiness rules.
- Create: `desktop_qt/state.py` for Qt UI state dataclasses.
- Create: `desktop_qt/models.py` for simple Qt list/table models.
- Create: `desktop_qt/app.py` for QApplication bootstrap.
- Create: `desktop_qt/main_window.py` for shell, navigation, stacked pages, timers, and controller wiring.
- Create: `desktop_qt/pages/home.py` for 首页运行.
- Create: `desktop_qt/pages/case_library.py` for 用例库.
- Create: `desktop_qt/pages/settings.py` for 运行配置.
- Create: `desktop_qt/pages/results.py` for 结果日志.
- Create: `desktop_qt/pages/devices.py` for 设备管理.
- Modify: `desktop_app.py` to launch `desktop_qt.app.main`.
- Create: `tests/test_qt_preflight.py` for readiness rules.
- Create: `tests/test_qt_home.py` for run blocking and run creation.
- Create: `tests/test_qt_shell.py` for main window smoke behavior.
- Create: `tests/test_qt_results.py` for command and artifact rendering.

### Task 1: Add PySide6 Dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update dependency file**

Add this line to `requirements.txt`:

```text
PySide6>=6.7.0
```

- [ ] **Step 2: Install dependencies**

Run:

```powershell
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Expected: PySide6 and test dependencies install successfully.

- [ ] **Step 3: Commit**

```powershell
git add requirements.txt
git commit -m "chore: add PySide6 dependency"
```

### Task 2: Implement Readiness Rules

**Files:**
- Create: `desktop_qt/__init__.py`
- Create: `desktop_qt/preflight.py`
- Test: `tests/test_qt_preflight.py`

- [ ] **Step 1: Write readiness tests**

Create `tests/test_qt_preflight.py`:

```python
from desktop.case_models import SavedCase, CaseStep
from desktop_qt.preflight import Severity, evaluate_case_readiness


def _settings():
    return {
        "base_web": {"host": "192.168.13.236", "username": "root", "password": "web-pass", "log_download_dir": "D:\\logs"},
        "ssh": {"host": "192.168.13.236", "username": "root", "password": "ssh-pass", "rrc_release_command": "release", "log_output_dir": "D:\\ssh"},
        "traffic": {
            "server_host": "10.88.149.164",
            "server_username": "root",
            "server_password": "traffic-pass",
            "server_downlink_target": "10.6.251.27",
            "server_downlink_port": 6011,
            "server_uplink_listen_port": 7011,
            "phone_uplink_target": "10.88.149.164",
            "phone_uplink_port": 7011,
            "phone_downlink_listen_port": 6011,
            "device_overrides": {"device-1": {"phone_ip": "10.6.251.27"}},
        },
        "common": {"delay_seconds": 5},
    }


def _case(name, actions):
    return SavedCase.new(name, [CaseStep.new(action, action, {}) for action in actions])


def test_downlink_requires_server_target():
    settings = _settings()
    settings["traffic"]["server_downlink_target"] = ""
    case = _case("下行灌包", ["traffic_server_downlink_start"])

    result = evaluate_case_readiness(case, settings, ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is True
    assert "下行灌包缺少服务器下行目标 IP" in result.blocking_messages
    assert any(item.severity == Severity.ERROR for group in result.groups for item in group.items)


def test_bidirectional_passes_when_uplink_and_downlink_are_complete():
    case = _case("双向灌包", ["traffic_server_downlink_start", "phone_uplink_iperf_start"])

    result = evaluate_case_readiness(case, _settings(), ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is False
    assert result.blocking_messages == []


def test_rrc_requires_web_and_ssh_passwords():
    settings = _settings()
    settings["base_web"]["password"] = ""
    settings["ssh"]["password"] = ""
    case = _case("RRC 测试用例", ["base_web_capture_start", "base_ssh_command_start"])

    result = evaluate_case_readiness(case, settings, ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is True
    assert "缺少基站 Web 密码" in result.blocking_messages
    assert "缺少基站 SSH 密码" in result.blocking_messages


def test_dual_mode_requires_each_device_phone_ip_mapping():
    settings = _settings()
    case = _case("下行灌包", ["traffic_server_downlink_start"])

    result = evaluate_case_readiness(case, settings, ["device-1", "device-2"], {"adb_ok": True}, run_mode="dual")

    assert result.blocked is True
    assert "双设备模式缺少 device-2 的手机 IP 映射" in result.blocking_messages
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_preflight.py -v
```

Expected: FAIL because `desktop_qt.preflight` does not exist.

- [ ] **Step 3: Create package and readiness implementation**

Create `desktop_qt/__init__.py`:

```python
"""PySide6 desktop UI for the mobile automation platform."""
```

Create `desktop_qt/preflight.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ReadinessItem:
    group: str
    label: str
    severity: Severity
    message: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class ReadinessGroup:
    name: str
    items: list[ReadinessItem] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    groups: list[ReadinessGroup]
    blocking_messages: list[str]

    @property
    def blocked(self) -> bool:
        return bool(self.blocking_messages)


def evaluate_case_readiness(
    case: Any,
    settings: dict[str, Any],
    selected_devices: list[str],
    preflight: dict[str, Any] | None = None,
    *,
    run_mode: str = "single",
) -> ReadinessResult:
    preflight = preflight or {}
    actions = _case_actions(case)
    items: list[ReadinessItem] = []

    _add_device_items(items, selected_devices, preflight)
    if _needs_web(actions):
        _add_required(items, "基站 Web", "Web 地址", settings.get("base_web", {}).get("host"), "缺少基站 Web 地址")
        _add_required(items, "基站 Web", "Web 密码", settings.get("base_web", {}).get("password"), "缺少基站 Web 密码")
    if _needs_ssh(actions):
        _add_required(items, "基站 SSH", "SSH 地址", settings.get("ssh", {}).get("host"), "缺少基站 SSH 地址")
        _add_required(items, "基站 SSH", "SSH 密码", settings.get("ssh", {}).get("password"), "缺少基站 SSH 密码")
    if _needs_traffic(actions):
        traffic = settings.get("traffic", {})
        _add_required(items, "灌包服务器", "服务器地址", traffic.get("server_host"), "缺少灌包服务器地址")
        _add_required(items, "灌包服务器", "服务器密码", traffic.get("server_password"), "缺少灌包服务器密码")
        if _needs_downlink(actions):
            _add_required(items, "灌包服务器", "下行目标 IP", traffic.get("server_downlink_target"), "下行灌包缺少服务器下行目标 IP")
        if _needs_uplink(actions):
            _add_required(items, "灌包服务器", "上行目标 IP", traffic.get("phone_uplink_target"), "上行灌包缺少手机上行目标 IP")
    if run_mode == "dual":
        _add_dual_mapping_items(items, settings.get("traffic", {}), selected_devices)

    groups = _group_items(items)
    blocking = [item.message for item in items if item.required and item.severity == Severity.ERROR]
    return ReadinessResult(groups=groups, blocking_messages=blocking)


def _case_actions(case: Any) -> set[str]:
    steps = getattr(case, "steps", None)
    if steps is None and isinstance(case, dict):
        steps = case.get("steps") or []
    actions = set()
    for step in steps or []:
        if isinstance(step, dict):
            action = step.get("action") or step.get("kind")
        else:
            action = getattr(step, "action", "")
        if action:
            actions.add(str(action))
    return actions


def _needs_web(actions: set[str]) -> bool:
    return any(action.startswith("base_web_") for action in actions)


def _needs_ssh(actions: set[str]) -> bool:
    return any(action.startswith("base_ssh_") for action in actions)


def _needs_traffic(actions: set[str]) -> bool:
    return _needs_downlink(actions) or _needs_uplink(actions) or any(action.startswith("traffic_server_") for action in actions)


def _needs_downlink(actions: set[str]) -> bool:
    return "traffic_server_downlink_start" in actions or "phone_downlink_receive_start" in actions


def _needs_uplink(actions: set[str]) -> bool:
    return "phone_uplink_iperf_start" in actions or "traffic_server_uplink_receive_start" in actions


def _add_device_items(items: list[ReadinessItem], selected_devices: list[str], preflight: dict[str, Any]) -> None:
    if selected_devices:
        items.append(ReadinessItem("手机端", "已选择设备", Severity.OK, f"已选择 {len(selected_devices)} 台设备"))
    else:
        items.append(ReadinessItem("手机端", "已选择设备", Severity.ERROR, "未选择手机设备"))
    if preflight.get("adb_ok", True):
        items.append(ReadinessItem("手机端", "ADB", Severity.OK, "ADB 正常"))
    else:
        items.append(ReadinessItem("手机端", "ADB", Severity.ERROR, "ADB 不可用"))


def _add_required(items: list[ReadinessItem], group: str, label: str, value: Any, missing_message: str) -> None:
    if str(value or "").strip():
        items.append(ReadinessItem(group, label, Severity.OK, "已配置"))
    else:
        items.append(ReadinessItem(group, label, Severity.ERROR, missing_message))


def _add_dual_mapping_items(items: list[ReadinessItem], traffic: dict[str, Any], selected_devices: list[str]) -> None:
    overrides = traffic.get("device_overrides") or {}
    for device_id in selected_devices:
        values = overrides.get(device_id) or {}
        if str(values.get("phone_ip") or values.get("server_downlink_target") or "").strip():
            items.append(ReadinessItem("多设备映射", device_id, Severity.OK, f"{device_id} 已映射"))
        else:
            items.append(ReadinessItem("多设备映射", device_id, Severity.ERROR, f"双设备模式缺少 {device_id} 的手机 IP 映射"))


def _group_items(items: list[ReadinessItem]) -> list[ReadinessGroup]:
    order = ["手机端", "基站 Web", "基站 SSH", "灌包服务器", "多设备映射"]
    return [
        ReadinessGroup(name, [item for item in items if item.group == name])
        for name in order
        if any(item.group == name for item in items)
    ]
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
python -m pytest tests/test_qt_preflight.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/__init__.py desktop_qt/preflight.py tests/test_qt_preflight.py
git commit -m "feat: add Qt readiness rules"
```

### Task 3: Build Qt Application Shell

**Files:**
- Create: `desktop_qt/state.py`
- Create: `desktop_qt/app.py`
- Create: `desktop_qt/main_window.py`
- Create: `desktop_qt/pages/home.py`
- Create: `desktop_qt/pages/case_library.py`
- Create: `desktop_qt/pages/settings.py`
- Create: `desktop_qt/pages/results.py`
- Create: `desktop_qt/pages/devices.py`
- Test: `tests/test_qt_shell.py`

- [ ] **Step 1: Write shell smoke test**

Create `tests/test_qt_shell.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [{"name": "下行灌包", "steps": [{"action": "traffic_server_downlink_start"}]}]

    def load_settings(self):
        return {"traffic": {}, "base_web": {}, "ssh": {}, "common": {}}

    def list_runs(self, limit=20):
        return []


def test_main_window_has_five_navigation_entries():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    labels = [window.nav_list.item(index).text() for index in range(window.nav_list.count())]

    assert labels == ["首页运行", "用例库", "运行配置", "结果日志", "设备管理"]
    assert window.stack.currentWidget() is window.home_page
    window.close()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_shell.py -v
```

Expected: FAIL because `desktop_qt.main_window` does not exist.

- [ ] **Step 3: Implement minimal shell and page placeholders**

Create `desktop_qt/state.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QtDesktopState:
    selected_devices: list[str] = field(default_factory=list)
    selected_case: Any | None = None
    selected_run_id: str = ""
    run_mode: str = "single"
    preflight: dict[str, Any] = field(default_factory=dict)
```

Create `desktop_qt/pages/home.py`:

```python
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class HomePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        self.device_label = QLabel("当前设备")
        self.case_label = QLabel("选择用例")
        self.readiness_label = QLabel("配置检查")
        self.start_button = QPushButton("开始测试")
        self.preflight_button = QPushButton("预检")
        self.live_label = QLabel("实时执行")
        layout.addWidget(self.device_label)
        layout.addWidget(self.case_label)
        layout.addWidget(self.readiness_label)
        layout.addWidget(self.preflight_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.live_label)
```

Create the four remaining page files with the same pattern:

```python
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CaseLibraryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("用例库"))
```

Use class names `SettingsPage`, `ResultsPage`, and `DevicesPage` in their respective files and labels `运行配置`, `结果日志`, and `设备管理`.

Create `desktop_qt/main_window.py`:

```python
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QListWidget, QMainWindow, QStackedWidget, QHBoxLayout, QWidget

from desktop.controller import DesktopController
from desktop_qt.pages.case_library import CaseLibraryPage
from desktop_qt.pages.devices import DevicesPage
from desktop_qt.pages.home import HomePage
from desktop_qt.pages.results import ResultsPage
from desktop_qt.pages.settings import SettingsPage
from desktop_qt.state import QtDesktopState


class MainWindow(QMainWindow):
    def __init__(self, *, controller=None, start_polling: bool = True):
        super().__init__()
        self.controller = controller or DesktopController()
        self.state = QtDesktopState()
        self.setWindowTitle("基站自动化测试平台")
        self.resize(1500, 900)
        self.nav_list = QListWidget()
        self.stack = QStackedWidget()
        self.home_page = HomePage(self)
        self.case_library_page = CaseLibraryPage(self)
        self.settings_page = SettingsPage(self)
        self.results_page = ResultsPage(self)
        self.devices_page = DevicesPage(self)
        self._build_layout()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_runs)
        if start_polling:
            self.poll_timer.start(2000)

    def _build_layout(self) -> None:
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.nav_list, 0)
        layout.addWidget(self.stack, 1)
        pages = [
            ("首页运行", self.home_page),
            ("用例库", self.case_library_page),
            ("运行配置", self.settings_page),
            ("结果日志", self.results_page),
            ("设备管理", self.devices_page),
        ]
        for label, page in pages:
            self.nav_list.addItem(label)
            self.stack.addWidget(page)
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)
        self.setCentralWidget(central)

    def refresh_runs(self) -> None:
        self.controller.list_runs(limit=20)
```

Create `desktop_qt/app.py`:

```python
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
```

- [ ] **Step 4: Run smoke test**

Run:

```powershell
python -m pytest tests/test_qt_shell.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt tests/test_qt_shell.py
git commit -m "feat: add PySide6 shell"
```

### Task 4: Implement 首页运行 Behavior

**Files:**
- Modify: `desktop_qt/pages/home.py`
- Modify: `desktop_qt/main_window.py`
- Test: `tests/test_qt_home.py`

- [ ] **Step 1: Write home workflow tests**

Create `tests/test_qt_home.py` with fake controller tests for:

```python
def test_home_blocks_start_when_required_config_missing():
    # Build MainWindow with one downlink case and missing server_downlink_target.
    # Click Start Test.
    # Assert controller.created is None and blocking text includes 下行灌包缺少服务器下行目标 IP.


def test_home_creates_run_when_readiness_passes():
    # Build MainWindow with one selected device, complete traffic settings, and one downlink case.
    # Click Start Test.
    # Assert controller.created == ("device-1", [case payload]).
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_home.py -v
```

Expected: FAIL because home page only has placeholder widgets.

- [ ] **Step 3: Implement device loading, case selection, readiness rendering, and start blocking**

In `HomePage`, add:

- device list widget
- run mode combo
- case list widget
- readiness list widget
- blocking message label
- live execution text widget
- `refresh_devices()`
- `load_cases()`
- `refresh_readiness()`
- `start_run()`

Connect Start Test to `start_run()` and Preflight to `refresh_readiness()`.

- [ ] **Step 4: Run home tests**

Run:

```powershell
python -m pytest tests/test_qt_home.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/pages/home.py desktop_qt/main_window.py tests/test_qt_home.py
git commit -m "feat: implement run-first home page"
```

### Task 5: Implement 运行配置 Cards

**Files:**
- Modify: `desktop_qt/pages/settings.py`
- Test: `tests/test_qt_settings.py`

- [ ] **Step 1: Write settings card test**

Create `tests/test_qt_settings.py`:

```python
def test_settings_page_saves_one_group_without_replacing_siblings():
    # Fake controller returns settings with base_web and traffic.
    # Edit base_web host.
    # Save base_web card.
    # Assert saved settings keep traffic.server_host unchanged.
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_settings.py -v
```

Expected: FAIL because settings cards do not exist.

- [ ] **Step 3: Implement settings page**

Create card widgets for:

- 基站 Web
- 基站 SSH
- 灌包服务器
- 多设备映射
- 通用

Each card loads values from `controller.load_settings()`, edits only its group, and saves through `controller.save_settings()` or `controller.save_settings_group()` when available.

- [ ] **Step 4: Run settings test**

Run:

```powershell
python -m pytest tests/test_qt_settings.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/pages/settings.py tests/test_qt_settings.py
git commit -m "feat: add Qt runtime settings cards"
```

### Task 6: Implement 用例库 Page

**Files:**
- Modify: `desktop_qt/pages/case_library.py`
- Test: `tests/test_qt_case_library.py`

- [ ] **Step 1: Write case library test**

Create `tests/test_qt_case_library.py`:

```python
def test_case_library_adds_selected_case_to_home_run_selection():
    # Fake controller returns one saved case with two steps.
    # Select the case on 用例库.
    # Click 加入运行.
    # Assert window.state.selected_case is that case and home readiness refreshes.
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_case_library.py -v
```

Expected: FAIL because case list and add-to-run behavior do not exist.

- [ ] **Step 3: Implement page layout**

Use:

- `QListWidget` for case list
- `QListWidget` or `QTreeWidget` for step timeline
- `QFormLayout` for selected step parameters
- bottom buttons: 保存, 复制, 导出, 加入运行

Use existing controller methods `get_templates`, `save_case`, `copy_case`, and `case_to_run_payload`.

- [ ] **Step 4: Run case library test**

Run:

```powershell
python -m pytest tests/test_qt_case_library.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/pages/case_library.py tests/test_qt_case_library.py
git commit -m "feat: add Qt case library page"
```

### Task 7: Implement 结果日志 Page

**Files:**
- Modify: `desktop_qt/pages/results.py`
- Create: `desktop_qt/models.py`
- Test: `tests/test_qt_results.py`

- [ ] **Step 1: Write results rendering test**

Create `tests/test_qt_results.py`:

```python
def test_results_page_renders_command_streams_and_artifacts():
    # Fake run has one SSH step with data.command, stdout, stderr, and artifacts.
    # Render the run.
    # Assert visible log text includes command, stdout, stderr, and artifact path.
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_results.py -v
```

Expected: FAIL because result rendering does not exist.

- [ ] **Step 3: Implement results page**

Use:

- left run list
- middle step timeline
- right read-only log text
- bottom artifact path list
- filter combo with 全部, ADB, SSH, Web 抓包, 灌包服务器, 错误

Reuse `desktop.formatters.format_run_console`, `extract_step_rows`, and `format_raw_json`.

- [ ] **Step 4: Run results test**

Run:

```powershell
python -m pytest tests/test_qt_results.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/pages/results.py desktop_qt/models.py tests/test_qt_results.py
git commit -m "feat: add Qt results log page"
```

### Task 8: Implement 设备管理 Page

**Files:**
- Modify: `desktop_qt/pages/devices.py`
- Test: `tests/test_qt_devices.py`

- [ ] **Step 1: Write device management test**

Create `tests/test_qt_devices.py`:

```python
def test_devices_page_persists_device_phone_ip_mapping():
    # Fake controller returns settings with empty traffic.device_overrides.
    # Enter mapping for device-1.
    # Save mapping.
    # Assert saved settings contain traffic.device_overrides.device-1.phone_ip.
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_qt_devices.py -v
```

Expected: FAIL because device mapping editor does not exist.

- [ ] **Step 3: Implement device management page**

Add:

- refresh devices button
- device list
- inspect device button
- ADB and iperf status labels
- editable mapping table for device id, phone IP, downlink port, uplink port
- save mapping button that updates `traffic.device_overrides`

- [ ] **Step 4: Run device test**

Run:

```powershell
python -m pytest tests/test_qt_devices.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add desktop_qt/pages/devices.py tests/test_qt_devices.py
git commit -m "feat: add Qt device management page"
```

### Task 9: Switch Entrypoint to PySide6

**Files:**
- Modify: `desktop_app.py`
- Test: `tests/test_desktop_ui_preview.py` or new `tests/test_qt_entrypoint.py`

- [ ] **Step 1: Write entrypoint test**

Create `tests/test_qt_entrypoint.py`:

```python
def test_desktop_app_imports_qt_entrypoint():
    import desktop_app

    assert callable(desktop_app.main)
```

- [ ] **Step 2: Modify entrypoint**

Update `desktop_app.py` so `main()` calls `desktop_qt.app.main()` after logging setup. Preserve `_configure_logging()` for packaged diagnostics.

- [ ] **Step 3: Run entrypoint and compile checks**

Run:

```powershell
python -m py_compile desktop_app.py desktop_qt/app.py desktop_qt/main_window.py
python -m pytest tests/test_qt_entrypoint.py tests/test_qt_shell.py -v
```

Expected: compile succeeds and tests pass.

- [ ] **Step 4: Commit**

```powershell
git add desktop_app.py tests/test_qt_entrypoint.py
git commit -m "feat: launch PySide6 desktop app"
```

### Task 10: Full Verification

**Files:**
- No new files unless tests reveal defects.

- [ ] **Step 1: Run targeted Qt tests**

Run:

```powershell
python -m pytest tests/test_qt_preflight.py tests/test_qt_shell.py tests/test_qt_home.py tests/test_qt_settings.py tests/test_qt_case_library.py tests/test_qt_results.py tests/test_qt_devices.py tests/test_qt_entrypoint.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 3: Launch manual smoke**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m desktop_qt.app
```

Expected: process starts without import or construction errors. For an interactive check, run without `QT_QPA_PLATFORM=offscreen` on a desktop session and confirm 首页运行 is first.

- [ ] **Step 4: Commit verification fixes if needed**

```powershell
git status --short
git add <changed-files>
git commit -m "fix: stabilize PySide6 desktop verification"
```

## Self-Review

Spec coverage:

- 首页运行, 用例库, 运行配置, 结果日志, and 设备管理 are each mapped to a task.
- Selected-case readiness rules are separated and tested before UI work.
- Start blocking, command visibility, artifact paths, and per-device mappings are covered.

Placeholder scan:

- The plan intentionally leaves implementation detail inside later UI tasks at component level because widget code will depend on PySide6 availability and existing controller behavior. No acceptance-critical behavior is left undefined.

Type consistency:

- `evaluate_case_readiness(case, settings, selected_devices, preflight, run_mode=...)` is the central readiness API used by tests and UI.
- `MainWindow.state` uses `QtDesktopState`.
- Page classes consistently receive `window` and access `window.controller` and `window.state`.
