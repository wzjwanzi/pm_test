# Phase 7 Result Handoff Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phase 5 confirmed that real-device runs produce durable `run.json` and `case.json` artifacts. Those JSON files can be large because snapshot steps capture full Android `dumpsys` output. Operators need a quick way to hand off a compact result summary and open the underlying artifact directory from the desktop app.

## Goal

Add a small, testable result handoff layer that exports a compact Markdown report for the selected run and lets the desktop app open the run artifact directory.

## Non-Goals

- Do not change PM execution behavior.
- Do not trim or rewrite existing `run.json` artifacts.
- Do not add a new database or report format engine.
- Do not rebuild release packages in this phase.

## Design

Create `desktop/artifacts.py` with pure helpers:

- `artifact_dir_for_run(run)` resolves the artifact directory from a run dictionary.
- `build_run_report(run)` creates a compact Markdown summary with run metadata, summary counts, and step rows from `desktop.formatters.extract_step_rows`.
- `export_run_report(run, output_dir=None)` writes the report as `run_report.md`, defaulting to the run artifact directory.
- `open_artifact_dir(run, opener=None)` validates the artifact directory and opens it through an injectable opener. On Windows the default opener is `os.startfile`.

Extend `DesktopController` with `export_run_report` and `open_artifact_dir` methods. Extend `ResultsPanel` with buttons for exporting the selected run report and opening the artifact directory. The app shell will route button actions through the controller and show a concise message.

## Error Handling

- Missing selected run: show a message and do nothing.
- Missing artifact directory: raise `ValueError` from the helper, caught by the app shell and displayed as a message.
- Non-existent artifact path: raise `FileNotFoundError`, caught by the app shell.

## Validation

- Unit tests for report generation, export path, opener injection, and controller delegation.
- Existing desktop shell test continues to validate panel creation.
- Full `python -m pytest -v`.

## Success Criteria

- Operators can export a compact `run_report.md` from a selected run.
- Operators can open the selected run artifact directory from the desktop app.
- Report content avoids dumping full raw JSON.
- Full test suite passes.
