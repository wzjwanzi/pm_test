# Phase 5 Real Device Validation Report

Date: 2026-05-15
Project: mobile_automation_platform

## Scope

Phase 5 validated the refactored platform against a connected Android device using the existing ADB, device discovery, PM preflight, PM run manager, and artifact persistence paths. No business-code changes were required during this validation pass.

## Device

- Device ID: `MKBUT20605024486`
- Model: `CDY-AN00`
- Android version: `10`
- ADB state: `device`

## Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate_real_device.ps1 -DeviceId MKBUT20605024486
```

The script performed:

- Local regression check with `python -m pytest -q`
- ADB device discovery
- Device model and Android version collection
- Project device discovery through `DeviceManager`
- PM device inspection through `PmTestRunManager.inspect_device`
- Minimal Ping-only PM run through `PmTestRunManager.create_run`
- Run artifact existence check

## Result

- Validation status: `completed`
- Pytest step: passed
- ADB discovery step: passed
- Device properties step: passed
- Project real run step: passed
- PM run ID: `pmrun-5fa50e514a0f`
- PM run status: `passed`
- PM run summary: total `1`, passed `1`, failed `0`, error `0`, skipped `0`

## Evidence

- Validation JSON: `artifacts/validation/phase5_real_device_validation.json`
- Run artifact directory: `artifacts/test_runs/pmrun-5fa50e514a0f`
- Run record: `artifacts/test_runs/pmrun-5fa50e514a0f/run.json`
- Case record: `artifacts/test_runs/pmrun-5fa50e514a0f/cases/001-case-001/case.json`

## Observations

- The real-device run completed through the refactored facade and persisted run/case JSON artifacts.
- The generated `run.json` and `case.json` are large because the snapshot step stores full Android `dumpsys` output.
- The minimal path used Ping-only execution with capture disabled and server action set to `none`.
- No release package rebuild was performed in Phase 5.

## Next Actions

- Consider trimming or externalizing verbose snapshot payloads before broad release if artifact size becomes an operational issue.
- Phase 6 can consolidate release packaging: promote the validated package, generate a delivery manifest, and archive the release directory.
