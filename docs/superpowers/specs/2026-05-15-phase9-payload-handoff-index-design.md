# Phase 9 Payload Handoff Index Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phase 8 moved oversized diagnostic strings from `run.json` and `case.json` into external payload files. This reduced JSON size while keeping full evidence. The remaining handoff gap is discoverability: `run_report.md` summarizes steps, but it does not list which full payload files were created.

## Goal

Add a compact external payload index to exported run reports so operators can find full diagnostic files without manually searching JSON.

## Non-Goals

- Do not change PM execution or payload externalization behavior.
- Do not rewrite historical reports automatically.
- Do not add a separate report format.
- Do not open individual payload files from the desktop UI in this phase.

## Design

Extend `desktop/artifacts.py`:

- Add `extract_external_payloads(run)` to scan case step artifacts for `kind == "external_payload"`.
- Return rows containing case name, step ID, label, path, byte count, and character count.
- Extend `build_run_report(run)` with an `External Payloads` Markdown table when payloads exist.
- Keep reports compact; do not inline payload previews or payload contents.

This keeps the reporting logic testable and avoids putting parsing logic into Tkinter widgets.

## Validation

- Unit tests for external payload extraction.
- Unit tests proving `build_run_report` includes an external payload table.
- Export a new report for the Phase 8 real-device run `pmrun-8b3a8b9e6dbb`.
- Full `python -m pytest -v`.

## Success Criteria

- `run_report.md` lists external payload files for runs that contain them.
- Reports without external payloads remain unchanged except for no payload table.
- Full tests pass.
