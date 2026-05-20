# Phase 5 Real Device Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the refactored platform against the connected Android device and record durable evidence.

**Architecture:** Run validation scripts through existing code paths (`DeviceManager`, `PmTestRunManager`, ADB, and artifact JSON) without changing business behavior unless a real defect is found.

**Tech Stack:** Python 3.11, pytest, ADB, existing PM core/facade, PowerShell.

---

## Task 1: Add Validation Script

**Files:**
- Create: `scripts/validate_real_device.ps1`

- [ ] Create a PowerShell script that accepts optional `-DeviceId`, runs pytest, ADB discovery, device properties, PM preflight, creates a Ping-only run, polls it briefly, and writes a JSON result file.
- [ ] The script must use project `adb.exe` and `python`.

## Task 2: Run Real Validation

**Files:**
- Output: `artifacts/validation/phase5_real_device_validation.json`

- [ ] Run `powershell -ExecutionPolicy Bypass -File scripts\validate_real_device.ps1 -DeviceId MKBUT20605024486`.
- [ ] If validation fails, inspect the recorded JSON and command output.

## Task 3: Fix Project Defects Only If Needed

**Files:**
- Modify only files directly related to any reproduced project defect.

- [ ] If a failure is caused by project code, write a focused failing test.
- [ ] Fix the defect.
- [ ] Re-run the relevant test and validation script.

## Task 4: Record Human-Readable Report

**Files:**
- Create: `docs/phase5_real_device_validation.md`

- [ ] Summarize device ID, validation commands, result states, artifact paths, failures, and next actions.
- [ ] Run `python -m pytest -v` after any code changes.
