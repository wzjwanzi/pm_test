# Phase 4 Final Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a delivery-ready package and final documentation for the refactored platform.

**Architecture:** Keep source behavior unchanged. Add final docs, parameterize package smoke verification, build into `release_phase4`, and verify the generated executable.

**Tech Stack:** Python 3.11, PyInstaller, PowerShell scripts, pytest.

---

## Task 1: Final Delivery Tests

**Files:**
- Create: `tests/test_final_delivery_files.py`

- [ ] Write tests that assert `scripts/verify_package.ps1` accepts `ExePath`, and final docs contain required commands.
- [ ] Run `python -m pytest tests/test_final_delivery_files.py -v` and confirm failure.

## Task 2: Scripts And Final Docs

**Files:**
- Modify: `scripts/verify_package.ps1`
- Create: `docs/user_quick_start.md`
- Create: `docs/final_delivery.md`

- [ ] Add optional `param([string]$ExePath)` to package verifier.
- [ ] Add quick start guide for desktop users.
- [ ] Add final delivery checklist and command summary.
- [ ] Run final delivery file tests and confirm pass.

## Task 3: Build And Verify

**Files:**
- Build outputs under `build_phase4/` and `release_phase4/`.

- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts/verify_dev.ps1`.
- [ ] Run `python -m PyInstaller build.spec --clean --noconfirm --distpath release_phase4 --workpath build_phase4`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts/verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe`.
- [ ] Run `python -m pytest -v`.

## Task 4: Report

**Files:**
- No extra files unless verification reveals needed fixes.

- [ ] Record final package path, verification evidence, and git limitation.
