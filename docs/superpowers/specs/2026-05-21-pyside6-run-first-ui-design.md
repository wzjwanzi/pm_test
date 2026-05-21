# PySide6 Run-First UI Design

Date: 2026-05-21
Project: mobile_automation_platform

## Context

The desktop application is currently a Tkinter shell launched from `desktop_app.py`. Most business behavior is already separated behind `desktop.controller.DesktopController`, `desktop.case_library.CaseLibrary`, `desktop.case_templates`, `app_settings`, and `pm_tests.PmTestRunManager`.

The next UI direction is a PySide6 desktop application focused on getting from opening the exe to starting a test as quickly and clearly as possible. The UI should stop presenting modules and parameters as the first mental model. Instead, it should show what the selected case needs, what is ready, what is missing, what will run, which commands were executed, and where files were generated.

## Goal

Build a PySide6 desktop UI where the default first screen is the test run workflow:

1. Confirm current device state.
2. Select one of the primary test cases.
3. Run or review configuration checks specific to the selected case.
4. Start the test with a clear blocking message if required configuration is missing.
5. Watch live step progress, command input, command output, and artifact paths.

## Non-Goals

This redesign does not change the PM execution core API.

This redesign does not change low-level ADB, SSH, Web capture, traffic server, or iperf execution behavior.

This redesign does not add a Web UI.

This redesign does not remove the existing Tkinter implementation until the PySide6 shell can be launched, tested, and packaged.

## Main Window

The main window uses a fixed left navigation with five entries:

- 首页运行
- 用例库
- 运行配置
- 结果日志
- 设备管理

The application opens directly on 首页运行. The left navigation changes pages only; it does not hide the current run state or reset selections.

## 首页运行

首页运行 is the primary workflow page, arranged from top to bottom in operation order.

### 1. 当前设备

The device section shows:

- connected Android devices
- single-phone or dual-phone run mode
- selected device ids
- phone IP mapping status
- `device-1 -> IP` and `device-2 -> IP` when mappings exist

The page must clearly distinguish:

- no device connected
- one device connected and selected
- multiple devices connected but no run mode selected
- dual-device mode selected but only one usable mapping exists

### 2. 选择用例

The first-screen case choices are:

- 下行灌包
- 上行灌包
- 双向灌包
- RRC 测试用例
- 入网

Selecting a case updates the configuration check list immediately. Saved custom cases remain available from 用例库 and can be sent to 首页运行.

### 3. 配置检查

Configuration status is calculated for the selected case, not globally. Each check item has one of three states:

- green: complete
- yellow: runnable but recommended values are missing or weak
- red: missing or invalid, run is blocked

The check groups are:

- 基站 Web: configured, missing password, connection exception, capture path visibility
- 基站 SSH: configured, missing password, required command missing
- 灌包服务器: configured, target IP missing, server credentials missing
- 手机端: ADB usable, iperf binary exists, device selected
- 多设备映射: selected device ids mapped to phone IPs and per-device ports

The preflight button refreshes device, ADB, optional iperf, and connection-derived status. Static settings checks update whenever settings, device selection, or selected case changes.

### 4. 开始运行

The start area contains:

- a primary Start Test button
- a secondary Preflight button
- a concise run-blocking message when required items are red

Clicking Start Test with blocking problems does not start a run. It highlights the missing items and shows exact Chinese messages, for example:

- 缺少基站 SSH 密码
- 双设备模式缺少 device-2 的手机 IP 映射
- 下行灌包缺少服务器下行目标 IP

### 5. 实时执行

The live execution area shows:

- current case and step
- step timeline
- command input
- command stdout
- command stderr
- pcap path
- SSH log path
- other generated artifact paths

The display is append-friendly for running tests and can render historical run records with the same structure.

## 运行配置

运行配置 contains focused cards:

- 基站 Web
- 基站 SSH
- 灌包服务器
- 多设备映射
- 通用

Each card header shows status:

- green: complete
- yellow: runnable but recommended values are missing
- red: missing and blocks at least one selected or common case

Saving a card updates only that settings group. The page uses the existing `app_settings` persistence model and should not replace unrelated groups when saving one card.

## 用例库

用例库 separates editing concerns:

- left: saved case list and default templates
- middle: selected case step timeline
- right: selected step parameters
- bottom: save, copy, export, add to run

The case library should no longer mix templates, run queue, step parameters, and device selection in one panel. "加入运行" sends the selected saved case to 首页运行 without starting it.

## 结果日志

结果日志 focuses on complete command visibility:

- left: historical run list
- middle: step result timeline
- right: real-time or historical log details
- bottom: artifact paths

Logs can be filtered by:

- 全部
- ADB
- SSH
- Web 抓包
- 灌包服务器
- 错误

For every rendered step, the UI should preserve:

- command input
- stdout
- stderr
- return or parsed result
- error
- artifact paths

## 设备管理

设备管理 contains device discovery and mapping tools:

- refresh connected devices
- inspect selected device
- show ADB status
- show iperf installation status
- edit per-device traffic mapping
- persist `traffic.device_overrides`

Device management is not the main run workflow; it exists for troubleshooting and explicit mapping edits.

## Architecture

PySide6 code lives in a new `desktop_qt` package while existing Tkinter code remains in `desktop` during migration.

The PySide6 UI reuses:

- `desktop.controller.DesktopController` for devices, cases, runs, settings, artifacts
- `desktop.case_models` and `desktop.case_library` for saved cases
- `desktop.case_templates` for default cases and step definitions
- `app_settings` for persistence and normalization
- `desktop.formatters` for existing run output extraction where useful

New PySide6-specific modules:

- `desktop_qt/app.py`: application bootstrap and top-level window creation
- `desktop_qt/main_window.py`: shell, left navigation, stacked pages, shared state wiring
- `desktop_qt/state.py`: selected page, selected devices, selected case, selected run, preflight result
- `desktop_qt/preflight.py`: selected-case requirements and status calculation
- `desktop_qt/pages/home.py`: 首页运行
- `desktop_qt/pages/case_library.py`: 用例库
- `desktop_qt/pages/settings.py`: 运行配置
- `desktop_qt/pages/results.py`: 结果日志
- `desktop_qt/pages/devices.py`: 设备管理
- `desktop_qt/models.py`: small table/list models for Qt views

The existing `desktop_app.py` remains the executable entrypoint. It should launch the PySide6 app by default once the PySide6 shell is ready. A fallback entrypoint for Tkinter can remain during migration.

## Data Flow

The selected case drives requirements:

1. User selects a case on 首页运行 or sends a case from 用例库.
2. `desktop_qt.preflight.evaluate_case_readiness(case, settings, devices, preflight)` returns grouped readiness items.
3. 首页运行 renders green/yellow/red status.
4. Start Test calls the same readiness function.
5. If any required item is red, the run is blocked and exact messages are shown.
6. If all required items pass, the selected case is converted through `DesktopController.case_to_run_payload`.
7. `DesktopController.create_run` starts one or more runs based on single-device or dual-device mode.
8. A Qt timer polls `list_runs` and `get_run` to update live results.

## Readiness Rules

Readiness rules are data-driven enough to test without a GUI.

Downlink traffic requires:

- selected device
- ADB visibility
- phone IP target for server downlink
- traffic server host, username, password
- downlink ports
- phone downlink listen port

Uplink traffic requires:

- selected device
- ADB visibility
- phone uplink target, usually traffic server IP
- traffic server host, username, password
- uplink listen port
- phone uplink port

Bidirectional traffic requires both downlink and uplink requirements.

RRC test requires:

- selected device
- base Web host, username, password
- base SSH host, username, password
- RRC release command or default command availability
- capture output directory

Attach test requires:

- selected device
- ADB visibility
- detach and attach wait settings

Dual-device mode additionally requires each selected device to have a phone IP mapping in `traffic.device_overrides`.

## Error Handling

Controller exceptions are caught at page action boundaries and rendered in the active page.

Blocking readiness failures are not exceptions. They are normal UI state and must be visible before the user clicks Start Test.

Long command output is never compressed into status labels. It belongs in the live execution panel or results log panel.

## Testing Strategy

Automated tests should not require real devices.

Required coverage:

- readiness rule tests for each primary case and dual-device mapping
- Qt smoke test that instantiates the main window with fake controller dependencies
- home page test that blocks Start Test when required items are missing
- home page test that creates a run when required items pass
- settings page test that saves one card without replacing sibling settings
- results page test that renders command input, stdout, stderr, errors, and artifacts
- entrypoint compile test

Manual verification:

- launch the PySide6 app locally
- confirm 首页运行 is first
- confirm navigation switches all five pages
- confirm missing config blocks Start Test with exact messages
- confirm fake or historical run records show command input/output and artifact paths

## Migration Plan

1. Add PySide6 dependency and a `desktop_qt` package.
2. Implement readiness calculation and tests first.
3. Build the PySide6 shell and 首页运行 with fake-controller smoke tests.
4. Add remaining pages using existing business services.
5. Switch `desktop_app.py` to PySide6 when smoke tests pass.
6. Keep Tkinter files untouched until the PySide6 path is stable.

## Acceptance Criteria

- Opening the desktop app defaults to 首页运行.
- Left navigation contains only 首页运行, 用例库, 运行配置, 结果日志, 设备管理.
- The home page shows device state, case choice, selected-case configuration checks, Start Test, Preflight, and live execution.
- Start Test is blocked when selected-case required configuration is red.
- Readiness checks are covered by unit tests without a GUI.
- Results log view shows command input and output for ADB, SSH, Web capture, traffic server, and error records.
- Settings cards show green/yellow/red status and save independently.
- Existing controller, case library, settings persistence, and PM run manager are reused.
- `python -m pytest -v` passes after implementation.
