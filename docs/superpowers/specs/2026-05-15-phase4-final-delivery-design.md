# Phase 4 Final Delivery Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phases 1 through 3 refactored the execution core, rewrote the desktop shell, and added engineering verification and packaging metadata. The remaining work is to produce a delivery-ready package and final documentation that explains how to run and validate the system.

The existing `release/MobileTestPlatform/MobileTestPlatform.exe` predates the refactors, so it does not prove the current source tree packages correctly. The workspace is still not a git repository, so final delivery cannot include commits or tags.

## Goal

Create a final delivery checkpoint that includes:

- Fresh packaged executable built from the current source.
- Local and packaged verification evidence.
- User-facing run guide.
- Final acceptance checklist.
- Summary of changed architecture and operational commands.

## Non-Goals

Phase 4 will not change PM execution behavior.

Phase 4 will not redesign UI behavior.

Phase 4 will not delete existing `release`, `release_fixed`, or `release_ui_review` directories.

Phase 4 will not create git commits, tags, or branches because the workspace has no `.git` metadata.

## Packaging Strategy

Build the current source into a separate delivery directory:

```text
release_phase4/MobileTestPlatform/
```

Use `build.spec` with:

```powershell
python -m PyInstaller build.spec --clean --noconfirm --distpath release_phase4 --workpath build_phase4
```

This avoids deleting or overwriting the existing `release` directory. The final package smoke script should accept an exe path parameter so it can verify both the existing release and the phase 4 delivery build.

## Documentation Strategy

Add:

- `docs/final_delivery.md`: final overview, run commands, verification evidence, known limitations.
- `docs/user_quick_start.md`: concise operator guide for launching the desktop app, selecting devices, building cases, running tests, and reading results.

Update:

- `scripts/verify_package.ps1`: accept an optional `-ExePath` parameter.

## Verification Strategy

Run:

- `powershell -ExecutionPolicy Bypass -File scripts/verify_dev.ps1`
- PyInstaller build to `release_phase4`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_package.ps1 -ExePath release_phase4/MobileTestPlatform/MobileTestPlatform.exe`

If PyInstaller is missing, install or report the missing dependency clearly. If packaging fails because of environment limitations, keep source verification and document the packaging failure.

## Acceptance Criteria

- `release_phase4/MobileTestPlatform/MobileTestPlatform.exe` exists after build.
- Package smoke verifies the phase 4 exe starts and stays alive briefly.
- `docs/user_quick_start.md` exists.
- `docs/final_delivery.md` exists and records verification commands.
- `scripts/verify_package.ps1` supports a custom `-ExePath`.
- `python -m pytest -v` passes.
- Development verification script passes.
