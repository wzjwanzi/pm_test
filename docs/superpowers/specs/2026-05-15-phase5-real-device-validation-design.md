# Phase 5 Real Device Validation Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

The platform has been refactored through four phases and packaged into `release_phase4`. Automated tests and smoke checks pass, but real hardware validation is still required. ADB currently detects one connected Android device:

```text
MKBUT20605024486    device
```

The configured external environment includes base-station Web, SSH, traffic server, ping, capture, and iperf settings. These integrations should be validated incrementally so failures can be attributed to a specific boundary.

## Goal

Validate the refactored execution core and desktop/package integration against a real connected device and reachable lab environment. Record evidence, artifact paths, and any failures in a durable validation report.

## Non-Goals

Phase 5 will not redesign UI or execution architecture unless validation exposes a concrete defect.

Phase 5 will not run destructive cleanup on the device.

Phase 5 will not overwrite release directories or rebuild packages.

Phase 5 will not run long-duration traffic tests before the minimal Ping-only path is verified.

## Validation Sequence

Run validation in this order:

1. Local regression check with `python -m pytest -v`.
2. ADB device discovery and basic device properties.
3. API/device-manager discovery through project code.
4. PM preflight for the selected device.
5. Minimal Ping-only PM run.
6. Artifact inspection for `run.json` and case/step records.
7. Optional external adapter reachability checks for SSH/Web/traffic, limited to connection or metadata checks.

## Success Criteria

- The connected device remains visible through ADB.
- Project device discovery returns the connected device ID.
- Preflight returns a structured result rather than crashing.
- A minimal PM run can be created for the real device.
- The run reaches a terminal state or records a structured failure.
- `run.json` exists for the run.
- Validation findings are written to `docs/phase5_real_device_validation.md`.

## Failure Handling

If a step fails, capture:

- exact command or Python snippet
- exit code
- relevant output
- structured error payload if available
- root-cause hypothesis
- whether the issue is code, configuration, device state, or lab environment

Fix code only when the failure is caused by project behavior rather than device or lab configuration.
