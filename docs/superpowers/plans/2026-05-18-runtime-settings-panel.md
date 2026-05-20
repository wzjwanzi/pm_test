# Runtime Settings Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw JSON runtime settings editor with four business module form tabs that save reliably, show passwords in plain text, and keep the existing `settings.json` schema.

**Architecture:** Add a small pure mapping layer in `desktop/settings_forms.py` that converts between the persisted settings schema and four UI modules. Then rebuild `desktop/widgets/settings.py` around typed Tkinter controls that call the existing controller save/load APIs.

**Tech Stack:** Python 3.11, Tkinter/ttk, existing `app_settings.py`, pytest.

---

## File Structure

- Create `desktop/settings_forms.py`: pure form mapping and validation. It owns module definitions, typed field parsing, and merge logic.
- Modify `desktop/widgets/settings.py`: replace JSON editors with form controls backed by `desktop.settings_forms`.
- Modify `tests/test_app_settings.py`: add unit tests for form mapping, module save isolation, phone aggregation, and integer validation.
- No changes to runtime service code should be needed because persisted `settings.json` remains compatible.

This workspace is not a Git repository, so commit steps are explicitly skipped.

### Task 1: Add Four-Module Settings Mapping

**Files:**
- Create: `desktop/settings_forms.py`
- Modify: `tests/test_app_settings.py`

- [ ] **Step 1: Write failing tests for module extraction and isolated saves**

Append these tests to `tests/test_app_settings.py`:

```python
from desktop.settings_forms import (
    SettingsValidationError,
    extract_business_modules,
    merge_business_module,
)


def test_extract_business_modules_groups_runtime_settings_by_business_area():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["base_web"]["password"] = "web-pass"
    settings["ssh"]["password"] = "ssh-pass"
    settings["traffic"]["server_password"] = "server-pass"
    settings["iperf"]["host"] = "10.0.0.9"
    settings["ping"]["host"] = "10.0.0.10"
    settings["traffic"]["phone_uplink_target"] = "10.0.0.11"

    modules = extract_business_modules(settings)

    assert modules["base_web"]["password"] == "web-pass"
    assert modules["ssh"]["password"] == "ssh-pass"
    assert modules["traffic_server"]["server_password"] == "server-pass"
    assert modules["phone"]["iperf.host"] == "10.0.0.9"
    assert modules["phone"]["ping.host"] == "10.0.0.10"
    assert modules["phone"]["traffic.phone_uplink_target"] == "10.0.0.11"


def test_merge_base_web_module_preserves_other_business_modules():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["ssh"]["host"] = "10.88.149.164"
    settings["traffic"]["server_host"] = "10.88.149.200"
    settings["iperf"]["host"] = "10.88.149.201"

    merged = merge_business_module(
        settings,
        "base_web",
        {
            "host": "192.168.13.250",
            "port": "8500",
            "username": "web-user",
            "password": "plain-password",
            "log_download_dir": r"D:\web_logs",
            "capture_signal_enabled": True,
            "capture_data_enabled": False,
            "capture_fapi_interface": "FAPI3",
        },
    )

    assert merged["base_web"]["host"] == "192.168.13.250"
    assert merged["base_web"]["port"] == 8500
    assert merged["base_web"]["password"] == "plain-password"
    assert merged["ssh"]["host"] == "10.88.149.164"
    assert merged["traffic"]["server_host"] == "10.88.149.200"
    assert merged["iperf"]["host"] == "10.88.149.201"


def test_merge_traffic_server_module_preserves_phone_traffic_fields():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["traffic"]["phone_uplink_target"] = "10.0.0.11"
    settings["traffic"]["phone_downlink_listen_port"] = 6011

    merged = merge_business_module(
        settings,
        "traffic_server",
        {
            "server_host": "10.88.149.210",
            "server_port": "22",
            "server_username": "root",
            "server_password": "server-pass",
            "server_connect_timeout": "30",
            "server_log_dir": r"D:\server_logs",
            "server_downlink_target": "10.6.250.12",
            "server_downlink_port": "6012",
            "server_downlink_bandwidth": "300m",
            "server_downlink_duration": "5000",
            "server_downlink_packet_len": "1300",
            "server_uplink_listen_port": "7012",
            "server_ping_target": "10.6.250.1",
        },
    )

    assert merged["traffic"]["server_host"] == "10.88.149.210"
    assert merged["traffic"]["server_downlink_port"] == 6012
    assert merged["traffic"]["phone_uplink_target"] == "10.0.0.11"
    assert merged["traffic"]["phone_downlink_listen_port"] == 6011


def test_merge_phone_module_updates_iperf_ping_and_phone_traffic_fields():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    merged = merge_business_module(
        settings,
        "phone",
        {
            "iperf.tool": "iperf",
            "iperf.host": "10.88.149.220",
            "iperf.port": "6088",
            "iperf.bandwidth": "150m",
            "iperf.duration": "6000",
            "iperf.interval": "2",
            "iperf.packet_len": "1200",
            "iperf.protocol": "tcp",
            "ping.host": "10.88.149.221",
            "ping.count": "6",
            "traffic.phone_uplink_target": "10.88.149.222",
            "traffic.phone_uplink_port": "7013",
            "traffic.phone_uplink_bandwidth": "110m",
            "traffic.phone_uplink_duration": "7000",
            "traffic.phone_uplink_packet_len": "1250",
            "traffic.phone_downlink_listen_port": "6013",
            "traffic.phone_ping_target": "10.88.149.223",
        },
    )

    assert merged["iperf"]["tool"] == "iperf"
    assert merged["iperf"]["port"] == 6088
    assert merged["ping"]["host"] == "10.88.149.221"
    assert merged["ping"]["count"] == 6
    assert merged["traffic"]["phone_uplink_target"] == "10.88.149.222"
    assert merged["traffic"]["phone_downlink_listen_port"] == 6013


def test_merge_business_module_rejects_invalid_integer_before_persistence():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    with pytest.raises(SettingsValidationError) as exc:
        merge_business_module(settings, "ssh", {"port": "not-a-number"})

    assert "port" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests\test_app_settings.py -q
```

Expected: FAIL during import because `desktop.settings_forms` does not exist.

- [ ] **Step 3: Implement `desktop/settings_forms.py`**

Create `desktop/settings_forms.py` with:

```python
"""Business-module mapping for the runtime settings form UI."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SettingsField:
    key: str
    label: str
    kind: str = "text"
    choices: tuple[str, ...] = ()


class SettingsValidationError(ValueError):
    pass


MODULE_LABELS = {
    "base_web": "基站 Web",
    "ssh": "基站 SSH",
    "traffic_server": "灌包服务器",
    "phone": "手机端",
}

MODULE_FIELDS: dict[str, tuple[SettingsField, ...]] = {
    "base_web": (
        SettingsField("host", "地址"),
        SettingsField("port", "端口", "int"),
        SettingsField("username", "用户名"),
        SettingsField("password", "密码"),
        SettingsField("log_download_dir", "日志下载目录"),
        SettingsField("capture_signal_enabled", "抓取信令", "bool"),
        SettingsField("capture_data_enabled", "抓取数据", "bool"),
        SettingsField("capture_fapi_interface", "FAPI 接口", "choice", ("FAPI1", "FAPI3")),
    ),
    "ssh": (
        SettingsField("host", "地址"),
        SettingsField("port", "端口", "int"),
        SettingsField("username", "用户名"),
        SettingsField("password", "密码"),
        SettingsField("log_output_dir", "日志输出目录"),
        SettingsField("log_command", "日志命令", "multiline"),
        SettingsField("connect_timeout", "连接超时", "int"),
    ),
    "traffic_server": (
        SettingsField("server_host", "服务器地址"),
        SettingsField("server_port", "SSH 端口", "int"),
        SettingsField("server_username", "用户名"),
        SettingsField("server_password", "密码"),
        SettingsField("server_connect_timeout", "连接超时", "int"),
        SettingsField("server_log_dir", "日志目录"),
        SettingsField("server_downlink_target", "下行目标"),
        SettingsField("server_downlink_port", "下行端口", "int"),
        SettingsField("server_downlink_bandwidth", "下行带宽"),
        SettingsField("server_downlink_duration", "下行时长", "int"),
        SettingsField("server_downlink_packet_len", "下行包长", "int"),
        SettingsField("server_uplink_listen_port", "上行监听端口", "int"),
        SettingsField("server_ping_target", "Ping 目标"),
    ),
    "phone": (
        SettingsField("iperf.tool", "Iperf 工具", "choice", ("iperf", "iperf3")),
        SettingsField("iperf.host", "Iperf 目标"),
        SettingsField("iperf.port", "Iperf 端口", "int"),
        SettingsField("iperf.bandwidth", "Iperf 带宽"),
        SettingsField("iperf.duration", "Iperf 时长", "int"),
        SettingsField("iperf.interval", "Iperf 间隔", "int"),
        SettingsField("iperf.packet_len", "Iperf 包长", "int"),
        SettingsField("iperf.protocol", "Iperf 协议", "choice", ("udp", "tcp")),
        SettingsField("ping.host", "Ping 目标"),
        SettingsField("ping.count", "Ping 次数", "int"),
        SettingsField("traffic.phone_uplink_target", "手机上行目标"),
        SettingsField("traffic.phone_uplink_port", "手机上行端口", "int"),
        SettingsField("traffic.phone_uplink_bandwidth", "手机上行带宽"),
        SettingsField("traffic.phone_uplink_duration", "手机上行时长", "int"),
        SettingsField("traffic.phone_uplink_packet_len", "手机上行包长", "int"),
        SettingsField("traffic.phone_downlink_listen_port", "手机下载监听端口", "int"),
        SettingsField("traffic.phone_ping_target", "手机 Ping 目标"),
    ),
}


def extract_business_modules(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    traffic = settings.get("traffic") or {}
    return {
        "base_web": dict(settings.get("base_web") or {}),
        "ssh": dict(settings.get("ssh") or {}),
        "traffic_server": {field.key: traffic.get(field.key) for field in MODULE_FIELDS["traffic_server"]},
        "phone": {
            "iperf.tool": (settings.get("iperf") or {}).get("tool"),
            "iperf.host": (settings.get("iperf") or {}).get("host"),
            "iperf.port": (settings.get("iperf") or {}).get("port"),
            "iperf.bandwidth": (settings.get("iperf") or {}).get("bandwidth"),
            "iperf.duration": (settings.get("iperf") or {}).get("duration"),
            "iperf.interval": (settings.get("iperf") or {}).get("interval"),
            "iperf.packet_len": (settings.get("iperf") or {}).get("packet_len"),
            "iperf.protocol": (settings.get("iperf") or {}).get("protocol"),
            "ping.host": (settings.get("ping") or {}).get("host"),
            "ping.count": (settings.get("ping") or {}).get("count"),
            "traffic.phone_uplink_target": traffic.get("phone_uplink_target"),
            "traffic.phone_uplink_port": traffic.get("phone_uplink_port"),
            "traffic.phone_uplink_bandwidth": traffic.get("phone_uplink_bandwidth"),
            "traffic.phone_uplink_duration": traffic.get("phone_uplink_duration"),
            "traffic.phone_uplink_packet_len": traffic.get("phone_uplink_packet_len"),
            "traffic.phone_downlink_listen_port": traffic.get("phone_downlink_listen_port"),
            "traffic.phone_ping_target": traffic.get("phone_ping_target"),
        },
    }


def merge_business_module(settings: dict[str, Any], module: str, values: dict[str, Any]) -> dict[str, Any]:
    if module not in MODULE_FIELDS:
        raise KeyError(f"Unknown settings module: {module}")
    merged = copy.deepcopy(settings)
    parsed = _parse_values(module, values)
    if module in {"base_web", "ssh"}:
        merged.setdefault(module, {}).update(parsed)
    elif module == "traffic_server":
        merged.setdefault("traffic", {}).update(parsed)
    elif module == "phone":
        for key, value in parsed.items():
            group, name = key.split(".", 1)
            merged.setdefault(group, {})[name] = value
    return merged


def merge_all_business_modules(settings: dict[str, Any], modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    merged = copy.deepcopy(settings)
    for module in MODULE_FIELDS:
        merged = merge_business_module(merged, module, modules.get(module, {}))
    return merged


def _parse_values(module: str, values: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for field in MODULE_FIELDS[module]:
        value = values.get(field.key, "")
        if field.kind == "int":
            try:
                parsed[field.key] = int(value)
            except (TypeError, ValueError) as exc:
                raise SettingsValidationError(f"{field.label} ({field.key}) must be an integer") from exc
        elif field.kind == "bool":
            parsed[field.key] = bool(value)
        else:
            parsed[field.key] = str(value)
    return parsed
```

- [ ] **Step 4: Run tests to verify Task 1 passes**

Run:

```powershell
python -m pytest tests\test_app_settings.py -q
```

Expected: PASS.

- [ ] **Step 5: Skip commit**

No commit command is run because `D:\test\mobile_automation_platform` is not a Git repository.

### Task 2: Replace JSON Settings Panel With Typed Forms

**Files:**
- Modify: `desktop/widgets/settings.py`
- Test: `tests/test_app_settings.py`

- [ ] **Step 1: Add an import-level smoke test for the new panel dependencies**

Append this test to `tests/test_app_settings.py`:

```python
def test_settings_panel_uses_business_module_definitions():
    from desktop.settings_forms import MODULE_FIELDS, MODULE_LABELS
    from desktop.widgets.settings import SettingsPanel

    assert SettingsPanel is not None
    assert list(MODULE_FIELDS) == ["base_web", "ssh", "traffic_server", "phone"]
    assert MODULE_LABELS["traffic_server"] == "灌包服务器"
```

- [ ] **Step 2: Run smoke test to verify current panel is not yet updated**

Run:

```powershell
python -m pytest tests\test_app_settings.py::test_settings_panel_uses_business_module_definitions -q
```

Expected: PASS after Task 1. This is a smoke guard before the UI rewrite.

- [ ] **Step 3: Replace `desktop/widgets/settings.py` with form-based implementation**

Update `desktop/widgets/settings.py` so it:

- Imports `MODULE_FIELDS`, `MODULE_LABELS`, `SettingsValidationError`, `extract_business_modules`, `merge_all_business_modules`, and `merge_business_module`.
- Keeps `SettingsPanel(ttk.LabelFrame)`.
- Uses `ttk.Notebook` with four tabs.
- Stores widgets in `self.field_vars` and `self.text_widgets`.
- Uses plain `ttk.Entry` for passwords, with no `show="*"`.
- Uses `ttk.Checkbutton` for bool fields and readonly `ttk.Combobox` for choices.
- Uses `ScrolledText` for multiline fields.
- Implements `load`, `save_group`, `save_current_group`, `save`, `reset`, `_collect_module_values`, and `_settings_path_text`.

The implementation should follow this shape:

```python
"""Runtime settings panel."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import config
from desktop.settings_forms import (
    MODULE_FIELDS,
    MODULE_LABELS,
    SettingsValidationError,
    extract_business_modules,
    merge_all_business_modules,
    merge_business_module,
)


class SettingsPanel(ttk.LabelFrame):
    def __init__(self, parent, app):
        super().__init__(parent, text="运行配置")
        self.app = app
        self.field_vars: dict[str, dict[str, tk.Variable]] = {}
        self.text_widgets: dict[str, dict[str, ScrolledText]] = {}
        self.module_order = list(MODULE_FIELDS)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        ttk.Button(controls, text="重新读取", command=self.load).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="保存当前模块", command=self.save_current_group).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(controls, text="保存全部", command=self.save).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(controls, text="恢复默认", command=self.reset).grid(row=0, column=3, padx=(0, 6))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        for module in self.module_order:
            self._build_module_tab(module)

    def _build_module_tab(self, module: str) -> None:
        frame = ttk.Frame(self.notebook, padding=8)
        frame.columnconfigure(1, weight=1)
        self.field_vars[module] = {}
        self.text_widgets[module] = {}
        for row, field in enumerate(MODULE_FIELDS[module]):
            ttk.Label(frame, text=field.label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            if field.kind == "bool":
                var = tk.BooleanVar(value=False)
                widget = ttk.Checkbutton(frame, variable=var)
            elif field.kind == "choice":
                var = tk.StringVar(value=field.choices[0] if field.choices else "")
                widget = ttk.Combobox(frame, textvariable=var, values=list(field.choices), state="readonly")
            elif field.kind == "multiline":
                widget = ScrolledText(frame, height=4, wrap="word")
                widget.grid(row=row, column=1, sticky="ew", pady=3)
                self.text_widgets[module][field.key] = widget
                continue
            else:
                var = tk.StringVar(value="")
                widget = ttk.Entry(frame, textvariable=var)
            widget.grid(row=row, column=1, sticky="ew", pady=3)
            self.field_vars[module][field.key] = var
        self.notebook.add(frame, text=MODULE_LABELS[module])

    def load(self) -> None:
        settings = self.app.controller.load_settings()
        modules = extract_business_modules(settings)
        for module, values in modules.items():
            self._set_module_values(module, values)

    def save_group(self, module: str) -> None:
        try:
            settings = self.app.controller.load_settings()
            values = self._collect_module_values(module)
            saved = self.app.controller.save_settings(merge_business_module(settings, module, values))
            self._set_module_values(module, extract_business_modules(saved)[module])
        except SettingsValidationError as exc:
            messagebox.showerror("配置格式错误", str(exc), parent=self)
            return
        self.app.set_message(f"{MODULE_LABELS[module]}配置已保存: {self._settings_path_text()}")

    def save_current_group(self) -> None:
        current_tab = self.notebook.select()
        current_index = self.notebook.index(current_tab)
        self.save_group(self.module_order[current_index])

    def save(self) -> None:
        try:
            settings = self.app.controller.load_settings()
            values = {module: self._collect_module_values(module) for module in self.module_order}
            saved = self.app.controller.save_settings(merge_all_business_modules(settings, values))
            modules = extract_business_modules(saved)
            for module, module_values in modules.items():
                self._set_module_values(module, module_values)
        except SettingsValidationError as exc:
            messagebox.showerror("配置格式错误", str(exc), parent=self)
            return
        self.app.set_message(f"配置已全部保存: {self._settings_path_text()}")

    def reset(self) -> None:
        settings = self.app.controller.reset_settings()
        modules = extract_business_modules(settings)
        for module, values in modules.items():
            self._set_module_values(module, values)
        self.app.set_message(f"配置已恢复默认: {self._settings_path_text()}")

    def _set_module_values(self, module: str, values: dict) -> None:
        for key, var in self.field_vars.get(module, {}).items():
            var.set(values.get(key, ""))
        for key, widget in self.text_widgets.get(module, {}).items():
            widget.delete("1.0", "end")
            widget.insert("end", str(values.get(key, "") or ""))

    def _collect_module_values(self, module: str) -> dict:
        values = {key: var.get() for key, var in self.field_vars.get(module, {}).items()}
        for key, widget in self.text_widgets.get(module, {}).items():
            values[key] = widget.get("1.0", "end").strip()
        return values

    def _settings_path_text(self) -> str:
        return str(config.SETTINGS_FILE)
```

- [ ] **Step 4: Run panel smoke test**

Run:

```powershell
python -m pytest tests\test_app_settings.py::test_settings_panel_uses_business_module_definitions -q
```

Expected: PASS.

- [ ] **Step 5: Run compile check**

Run:

```powershell
python -m py_compile desktop\widgets\settings.py desktop\settings_forms.py
```

Expected: exit code 0.

- [ ] **Step 6: Skip commit**

No commit command is run because `D:\test\mobile_automation_platform` is not a Git repository.

### Task 3: Full Verification And Package Readiness

**Files:**
- No production file changes expected.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
python -m pytest tests\test_app_settings.py tests\test_case_templates.py tests\test_desktop_controller.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run compile checks**

Run:

```powershell
python -m py_compile desktop\widgets\settings.py desktop\settings_forms.py app_settings.py
```

Expected: exit code 0.

- [ ] **Step 3: Run desktop import smoke**

Run:

```powershell
python -c "from desktop.widgets.settings import SettingsPanel; from desktop.settings_forms import MODULE_FIELDS; print(SettingsPanel.__name__, len(MODULE_FIELDS))"
```

Expected output includes:

```text
SettingsPanel 4
```

- [ ] **Step 4: Skip commit**

No commit command is run because `D:\test\mobile_automation_platform` is not a Git repository.

## Self-Review

Spec coverage:

- Four business modules are covered by Task 1 mapping and Task 2 UI tabs.
- Reliable save current/save all behavior is covered by mapping tests and UI methods.
- Passwords visible in plain text are covered by Task 2 using normal `ttk.Entry` with no mask.
- Existing `settings.json` schema is preserved because Task 1 writes back to the existing top-level groups.
- No automatic case remapping is added, matching the design.

Placeholder scan:

- No `TBD`, `TODO`, or unspecified implementation steps remain.

Type consistency:

- `MODULE_FIELDS`, `MODULE_LABELS`, `SettingsValidationError`, `extract_business_modules`, `merge_business_module`, and `merge_all_business_modules` are introduced in Task 1 and consumed in Task 2.

