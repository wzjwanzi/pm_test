# Phase 8 Artifact Payload Slimming

Date: 2026-05-15
Project: mobile_automation_platform

## Scope

Phase 8 keeps full diagnostic snapshot data while preventing oversized strings from being embedded directly in new `run.json` and `case.json` records.

## Behavior

When a step data string is larger than 4096 characters, the PM core writes the full value to a payload artifact and replaces the inline value with a compact reference.

Payload files are stored under the case artifact directory:

```text
payloads/<step-id>/<data-path>.txt
```

Example:

```text
artifacts/test_runs/<run-id>/cases/001-case-001/payloads/pre_snapshot/network_info-network_type.txt
```

## JSON Reference Shape

```json
{
  "type": "external_payload",
  "path": "payloads/pre_snapshot/network_info-network_type.txt",
  "bytes": 123456,
  "characters": 123456,
  "preview": "first compact text segment..."
}
```

The corresponding step also records an `external_payload` artifact with the same path and byte metadata.

## Constraints

- Historical artifacts are not rewritten.
- Short strings remain inline.
- Full payload files remain plain UTF-8 text for easy inspection.
- The feature applies to all oversized step data strings, not only snapshot steps.

## Verification

```powershell
python -m pytest tests\test_payloads.py tests\test_orchestrator.py -v
python -m pytest -v
powershell -ExecutionPolicy Bypass -File scripts\validate_real_device.ps1 -DeviceId MKBUT20605024486
```

## Real Device Evidence

Latest Phase 8 validation run:

- Run ID: `pmrun-8b3a8b9e6dbb`
- Status: `passed`
- `run.json`: `16725` bytes
- `case.json`: `15281` bytes
- External payload files: `4`
- External payload bytes: `391635`
- Artifact directory: `artifacts/test_runs/pmrun-8b3a8b9e6dbb`
