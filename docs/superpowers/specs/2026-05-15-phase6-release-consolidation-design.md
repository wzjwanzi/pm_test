# Phase 6 Release Consolidation Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phase 4 produced a PyInstaller package at `release_phase4/MobileTestPlatform/MobileTestPlatform.exe`. Phase 5 validated the refactored platform on a real Android device and wrote durable evidence to `artifacts/validation/phase5_real_device_validation.json`.

The workspace has no `.git` directory, so release consolidation cannot use commits, tags, or git diffs. The release process must be file-based and non-destructive.

## Goal

Create a reproducible release handoff package from the already validated Phase 4 executable, with a machine-readable manifest, checksum evidence, and human-readable delivery instructions.

## Non-Goals

- Do not rebuild the executable unless a later phase explicitly requests it.
- Do not delete or rename existing `release*` or `build*` directories.
- Do not change PM execution logic, desktop behavior, device discovery, or adapters.
- Do not require network access.

## Design

Add a PowerShell release script at `scripts/create_release_bundle.ps1`. The script will:

- Accept a release directory, output directory, version label, and validation JSON path.
- Verify that `MobileTestPlatform.exe` exists.
- Read the Phase 5 validation JSON and include validation status, device ID, run ID, and run status in the release manifest.
- Produce a zip archive under `artifacts/release`.
- Compute SHA-256 checksums for the executable and zip archive.
- Write `release_manifest.json` beside the zip.

Add a human-readable report at `docs/phase6_release_consolidation.md`. The report will document the script, expected artifacts, verification commands, and known constraints.

## Validation

Validation will use:

- Static pytest coverage for the release script and document.
- `python -m pytest -v`.
- `powershell -ExecutionPolicy Bypass -File scripts\create_release_bundle.ps1`.
- `powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe`.

## Success Criteria

- `scripts/create_release_bundle.ps1` exists and is non-destructive.
- `docs/phase6_release_consolidation.md` exists and references the generated manifest and zip.
- A release zip exists under `artifacts/release`.
- A release manifest exists under `artifacts/release/release_manifest.json`.
- Manifest includes executable checksum, zip checksum, Phase 5 validation status, real device ID, and PM run ID.
- Full pytest suite passes.
