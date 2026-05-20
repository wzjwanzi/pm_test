# Phase 6 Release Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the already validated Phase 4 executable into a reproducible release handoff with checksum and real-device validation evidence.

**Architecture:** Add one non-destructive PowerShell release script, one human-readable release report, and static pytest coverage that guards the expected release workflow.

**Tech Stack:** PowerShell, Python 3.11, pytest, existing PyInstaller output, existing Phase 5 validation JSON.

---

### Task 1: Add Release File Tests

**Files:**
- Create: `tests/test_phase6_release_files.py`

- [ ] Write tests that assert `scripts/create_release_bundle.ps1` contains parameterized release inputs, zip creation, checksum generation, validation JSON parsing, and manifest writing.
- [ ] Write tests that assert `docs/phase6_release_consolidation.md` references the release zip, manifest, Phase 5 validation JSON, and package verifier command.
- [ ] Run `python -m pytest tests/test_phase6_release_files.py -v` and confirm the tests fail because the files do not exist yet.

### Task 2: Add Release Script

**Files:**
- Create: `scripts/create_release_bundle.ps1`

- [ ] Implement a PowerShell script with parameters `-ReleaseDir`, `-OutputDir`, `-Version`, and `-ValidationJson`.
- [ ] Verify `MobileTestPlatform.exe` exists in the release directory.
- [ ] Load the Phase 5 validation JSON and extract validation status, device ID, PM run ID, PM run status, and run artifact path.
- [ ] Create `artifacts/release/MobileTestPlatform-<Version>.zip` with `Compress-Archive`.
- [ ] Compute SHA-256 for the executable and zip.
- [ ] Write `artifacts/release/release_manifest.json`.

### Task 3: Add Release Report

**Files:**
- Create: `docs/phase6_release_consolidation.md`

- [ ] Document the release source, command, generated files, manifest fields, verification commands, and constraints.

### Task 4: Verify Release Consolidation

**Files:**
- Output: `artifacts/release/MobileTestPlatform-phase6-20260515.zip`
- Output: `artifacts/release/release_manifest.json`

- [ ] Run `python -m pytest tests/test_phase6_release_files.py -v`.
- [ ] Run `python -m pytest -v`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts\create_release_bundle.ps1 -Version phase6-20260515`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe`.
- [ ] Inspect `artifacts/release/release_manifest.json` for expected checksums and validation fields.
