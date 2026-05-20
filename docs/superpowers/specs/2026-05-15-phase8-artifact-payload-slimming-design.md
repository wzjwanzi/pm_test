# Phase 8 Artifact Payload Slimming Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Real-device validation showed that snapshot steps can store very large Android `dumpsys` payloads inside `run.json` and `case.json`. This makes summary artifacts harder to inspect, copy, and hand off. Phase 7 added compact `run_report.md`, but the underlying JSON records are still large.

## Goal

Keep full diagnostic evidence while preventing oversized nested strings from being embedded directly in run and case JSON records.

## Non-Goals

- Do not remove snapshot collection.
- Do not change adapter success/failure behavior.
- Do not rewrite historical artifacts.
- Do not add compression or database storage.

## Design

Add `pm_tests/core/payloads.py` with a focused payload externalizer:

- Walk step `data` recursively.
- For strings larger than a threshold, write the full value to a deterministic file under the case artifact directory.
- Replace the original string with a compact reference object containing type, path, byte count, character count, and preview.
- Append an `Artifact` record to the step so UI/reporting can discover the external payload.

Integrate this into `CaseExecutor.execute` immediately after each `StepRecord` is returned by `StepRunner` and before `case.json` or `run.json` is written. This keeps in-memory records, case JSON, run JSON, desktop summaries, and API responses compact for new runs.

Default threshold: 4096 characters. The externalizer is generic and not snapshot-specific, but Phase 8 targets snapshot payloads.

## File Layout

Externalized files are stored below each case artifact directory:

```text
artifacts/test_runs/<run-id>/cases/<case>/payloads/<step-id>/<data-path>.txt
```

Example:

```text
payloads/pre_snapshot/network_info-network_type.txt
payloads/pre_snapshot/cell_info-cell_info.txt
```

## Error Handling

- If payload writing fails, allow the exception to surface and mark the run through existing orchestrator error handling.
- Non-string values remain unchanged.
- Short strings remain unchanged.

## Validation

- Unit tests for recursive string externalization, artifact registration, and short-string preservation.
- Orchestrator test proving `case.json` stores references and writes payload files.
- Full `python -m pytest -v`.
- Optional real-device validation to confirm new `run.json` size is materially smaller.

## Success Criteria

- New snapshot runs write large payloads to separate files.
- `run.json` and `case.json` contain compact references instead of full large strings.
- Full payload files are present under the case artifact directory.
- Existing tests continue to pass.
