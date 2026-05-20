# Phase 7 Result Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add desktop result handoff actions for exporting a compact run report and opening the selected run's artifact directory.

**Architecture:** Put filesystem/report logic in `desktop/artifacts.py`, expose it through `DesktopController`, and keep UI widgets as thin command surfaces.

**Tech Stack:** Python 3.11, Tkinter, pytest, existing desktop formatter helpers.

---

### Task 1: Artifact Helper Tests

**Files:**
- Create: `tests/test_desktop_artifacts.py`

- [ ] Write a failing test for `build_run_report(run)` that expects run ID, device ID, status, summary counts, and step rows without raw JSON braces.
- [ ] Write a failing test for `export_run_report(run)` that writes `run_report.md` into a temporary artifact directory.
- [ ] Write a failing test for `open_artifact_dir(run, opener=...)` that records the opened path without launching Explorer.
- [ ] Run `python -m pytest tests\test_desktop_artifacts.py -v` and confirm import failure for `desktop.artifacts`.

### Task 2: Implement Artifact Helpers

**Files:**
- Create: `desktop/artifacts.py`

- [ ] Implement `artifact_dir_for_run`, `build_run_report`, `export_run_report`, and `open_artifact_dir`.
- [ ] Use `extract_step_rows` from `desktop.formatters`.
- [ ] Keep output Markdown compact and deterministic.
- [ ] Run `python -m pytest tests\test_desktop_artifacts.py -v`.

### Task 3: Controller and UI Wiring

**Files:**
- Modify: `desktop/controller.py`
- Modify: `desktop/main.py`
- Modify: `desktop/widgets/results.py`
- Modify: `tests/test_desktop_controller.py`

- [ ] Add controller tests for `export_run_report` and `open_artifact_dir` using a fake opener.
- [ ] Run the controller test and confirm failure before implementation.
- [ ] Add controller methods delegating to `desktop.artifacts`.
- [ ] Add buttons to `ResultsPanel`.
- [ ] Add `DesktopApp.export_selected_run_report` and `DesktopApp.open_selected_run_artifacts`.
- [ ] Run desktop-related tests.

### Task 4: Documentation and Verification

**Files:**
- Create: `docs/phase7_result_handoff.md`

- [ ] Document the new desktop actions, generated `run_report.md`, and constraints.
- [ ] Run `python -m pytest -v`.
