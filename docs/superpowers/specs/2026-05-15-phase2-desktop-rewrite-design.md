# Phase 2 Desktop Rewrite Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phase 1 introduced a typed PM execution core and a compatibility facade exposed as `pm_tests.PmTestRunManager`. The desktop application still lives mostly in `desktop_app.py`, which is a large Tkinter file that mixes application startup, layout construction, settings forms, device actions, case building, run monitoring, and result formatting.

Project notes state that users primarily use the packaged desktop exe, so phase 2 focuses on the Tkinter desktop path. The Web UI remains a compatibility surface and is not redesigned in this phase.

The workspace is not a git repository, so design and implementation changes cannot be committed here.

## Goal

Rewrite the desktop application structure around the phase 1 execution core while preserving the existing executable entrypoint. The new desktop app should provide a clearer workflow:

1. Select or refresh a device.
2. Run preflight checks.
3. Build a queue of cases from operation templates.
4. Start, stop, and refresh a run.
5. Monitor run, case, and step status from the typed records.
6. Inspect result details, errors, artifacts, and raw JSON.
7. Edit runtime settings.

## Non-Goals

Phase 2 will not redesign `templates/index.html`.

Phase 2 will not change the phase 1 execution core API except for small compatibility fixes discovered during desktop integration.

Phase 2 will not introduce a new GUI framework. Tkinter remains the GUI toolkit to reduce packaging risk.

Phase 2 will not clean release/build artifacts or change the PyInstaller packaging strategy beyond preserving the `desktop_app.py` entrypoint.

## Architecture

The old `desktop_app.py` becomes a thin entrypoint responsible for logging setup, frozen environment preparation, Tk imports, and launching the new desktop shell.

New desktop code lives under a focused package:

- `desktop/main.py`: application shell, root layout, polling lifecycle.
- `desktop/state.py`: dataclasses for selected device, case queue, selected run, messages, and runtime view state.
- `desktop/controller.py`: thin service layer around `PmTestRunManager`, `DeviceManager`, and settings helpers.
- `desktop/widgets/devices.py`: device list and preflight panel.
- `desktop/widgets/cases.py`: operation templates and case queue editor.
- `desktop/widgets/run_monitor.py`: run controls, run history, and step timeline.
- `desktop/widgets/results.py`: selected run/case/step inspector, artifacts, raw JSON view.
- `desktop/widgets/settings.py`: runtime settings editor.

Widgets receive a controller and a shared state object. Widgets do not import `pm_tests` or device modules directly.

## UI Layout

The new desktop shell uses a three-column workbench inside a vertically safe window:

- Left rail: device list, selected device, preflight status, operation templates.
- Center workspace: case queue, run controls, current run timeline, step table.
- Right inspector: selected case details, selected step details, structured errors, artifacts, and raw JSON.

A compact header shows product name, selected device, current run status, and summary counts. Controls are dense and operational rather than marketing-style.

All main content must remain reachable in the default 1220x860 window. Scrolling is allowed inside large panels, but critical controls must stay visible:

- Refresh devices
- Run preflight
- Add case
- Start run
- Stop run
- Refresh run

## Data Flow

The controller exposes these methods:

- `refresh_devices() -> list[str]`
- `inspect_device(device_id: str) -> dict`
- `get_templates() -> list[dict]`
- `create_run(device_id: str, cases: list[dict]) -> dict`
- `request_stop(run_id: str) -> dict | None`
- `get_run(run_id: str) -> dict | None`
- `list_runs(limit: int = 20) -> list[dict]`
- `load_settings() -> dict`
- `save_settings(settings: dict) -> dict`
- `reset_settings() -> dict`

The UI reads run state from the phase 1 typed/compatibility shape:

- Prefer `status`.
- Fall back to `state`.
- Prefer `case_records` and `step_records`.
- Fall back to legacy `results` and text steps only when typed records are absent.

## Error Handling

Controller methods let exceptions propagate to widgets. Widgets catch exceptions at user action boundaries and render short Chinese messages in the relevant panel.

Structured adapter errors should show:

- error code
- adapter
- message
- recoverability
- details JSON when available

Long raw output belongs in the raw JSON/result panel, not in status labels.

## Testing Strategy

The rewrite must have automated tests that do not require real devices:

- Controller tests use fake `PmTestRunManager` and fake `DeviceManager`.
- State tests verify case queue operations.
- Formatter tests verify new UI helpers can normalize `RunRecord`-style dictionaries and legacy dictionaries.
- Tk smoke tests instantiate the shell with fake controller dependencies and verify critical widgets exist.

Manual verification should still compile `desktop_app.py` and run a Tk initialization smoke test without showing a real window.

## Migration Approach

Implement the new package alongside the existing `desktop_app.py`. Once the new shell passes smoke tests, replace `DesktopApp` in `desktop_app.py` with a compatibility alias/import from `desktop.main`.

Keep `_configure_logging`, `_prepare_frozen_gui_environment`, `_import_tk_modules`, and `main()` available from `desktop_app.py` because build scripts and manual smoke commands already use them.

The old monolithic implementation can remain in history only if this were a git repository. In this workspace, the practical result should be that `desktop_app.py` is small and delegates to the new package.

## Acceptance Criteria

- `desktop_app.py` is a thin entrypoint and no longer contains the full UI implementation.
- The desktop package has separate modules for shell, state, controller, and widgets.
- The desktop shell can be instantiated in a hidden Tk root during tests.
- Device refresh, preflight, case queue, start run, stop run, run history, result details, and settings are represented in the new UI.
- UI run rendering uses `status`, `case_records`, and `step_records` from phase 1 records.
- Automated tests cover state, controller, formatters, and Tk shell smoke behavior using fakes.
- `python -m pytest -v` passes.
- `python -m py_compile desktop_app.py desktop/main.py desktop/controller.py desktop/state.py` passes.
