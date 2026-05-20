# Production Desktop Workbench UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved preview layout to the production Tk desktop app while preserving existing controller and execution behavior.

**Architecture:** Rebuild `DesktopApp._build_layout()` into a reference-style top toolbar plus three-column workbench. Reuse existing devices, cases, results, run monitor, and settings widgets so behavior remains stable, and add a lightweight inspector panel for case summary and parameter table.

**Tech Stack:** Python 3.11, Tkinter/ttk, pytest.

---

## File Structure

- Modify: `desktop/main.py`
  - Owns production shell layout, toolbar, pane placement, and compatibility attributes.
- Create: `desktop/widgets/inspector.py`
  - Owns right-side case summary and parameter table.
- Modify: `tests/test_desktop_shell.py`
  - Adds assertions for the new workbench layout while keeping existing behavior tests.

## Implementation Tasks

### Task 1: Production Workbench Layout Test

**Files:**
- Modify: `tests/test_desktop_shell.py`

- [ ] Add a failing test that builds `DesktopApp` and asserts these attributes exist: `toolbar`, `workbench`, `left_pane`, `center_pane`, `right_pane`, and `inspector_panel`.
- [ ] Assert cases are above devices in the left pane by checking `app.cases_panel.grid_info()["row"] < app.devices_panel.grid_info()["row"]`.
- [ ] Assert runtime settings are no longer gridded as a permanent first-screen panel by checking `not app.settings_panel.winfo_ismapped()`.

### Task 2: Inspector Panel

**Files:**
- Create: `desktop/widgets/inspector.py`

- [ ] Implement `InspectorPanel(ttk.LabelFrame)` with `case_summary` and `parameter_table`.
- [ ] Add `render_case(case)` that shows the case name, description, step count, and each step parameter.
- [ ] Add `render_run(run)` that keeps the selected case details intact and does not crash when called with run dictionaries.

### Task 3: Production Layout

**Files:**
- Modify: `desktop/main.py`

- [ ] Replace the old header/body layout with a dark-blue toolbar and three-column workbench.
- [ ] Place `CasesPanel` at left row 0 and `DevicesPanel` at left row 1.
- [ ] Place `ResultsPanel` at center row 0 and `RunMonitorPanel` at center row 1.
- [ ] Place `InspectorPanel` in the right pane.
- [ ] Instantiate `SettingsPanel` but do not grid it in the first-screen layout.
- [ ] Preserve existing app attributes used by tests and controller flows.

### Task 4: Verification

**Commands:**

```powershell
python -m pytest tests\test_desktop_shell.py -v
python -m py_compile desktop_app.py desktop\main.py desktop\widgets\inspector.py
```

Expected: tests pass and compilation exits with status 0.
