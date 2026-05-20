# Phase 9 Payload Handoff Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an external payload index to exported run reports.

**Architecture:** Keep all report extraction logic in `desktop/artifacts.py`; no PM execution changes are needed.

**Tech Stack:** Python 3.11, Markdown, pytest, existing desktop artifact helpers.

---

### Task 1: Report Tests

**Files:**
- Modify: `tests/test_desktop_artifacts.py`

- [ ] Add a failing test for `extract_external_payloads(run)` with a run containing `external_payload` artifacts.
- [ ] Add a failing test that `build_run_report(run)` includes an `External Payloads` table.
- [ ] Run `python -m pytest tests\test_desktop_artifacts.py -v` and confirm failures.

### Task 2: Report Implementation

**Files:**
- Modify: `desktop/artifacts.py`

- [ ] Implement `extract_external_payloads(run)`.
- [ ] Add the payload table to `build_run_report`.
- [ ] Keep cell escaping consistent with the existing step table.
- [ ] Run `python -m pytest tests\test_desktop_artifacts.py -v`.

### Task 3: Docs and Verification

**Files:**
- Create: `docs/phase9_payload_handoff_index.md`

- [ ] Document the new `External Payloads` section.
- [ ] Export a new `run_report.md` for `pmrun-8b3a8b9e6dbb`.
- [ ] Run `python -m pytest -v`.
- [ ] Build and package `release_phase9`.
