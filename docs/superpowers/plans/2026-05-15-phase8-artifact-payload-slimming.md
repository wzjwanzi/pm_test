# Phase 8 Artifact Payload Slimming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Externalize oversized step data strings so run/case JSON stays compact while full diagnostic payloads remain available as artifacts.

**Architecture:** Add a payload externalizer in `pm_tests/core/payloads.py` and call it from `CaseExecutor` before records are written.

**Tech Stack:** Python 3.11, pathlib, pytest, existing PM core dataclasses.

---

### Task 1: Payload Externalizer Tests

**Files:**
- Create: `tests/test_payloads.py`

- [ ] Write a failing test that passes nested step data with a long string and expects a reference object plus a payload file.
- [ ] Write a failing test that confirms short strings remain inline.
- [ ] Write a failing test that confirms a step artifact is appended for each external payload.
- [ ] Run `python -m pytest tests\test_payloads.py -v` and confirm `pm_tests.core.payloads` is missing.

### Task 2: Implement Payload Externalizer

**Files:**
- Create: `pm_tests/core/payloads.py`

- [ ] Implement `externalize_large_step_payloads(step_record, case_dir, threshold=4096)`.
- [ ] Recursively walk dictionaries and lists.
- [ ] Write large strings to `payloads/<step-id>/<data-path>.txt`.
- [ ] Replace large strings with reference dictionaries.
- [ ] Append `Artifact(kind="external_payload", path=<path>, label=<data path>, metadata=...)`.
- [ ] Run `python -m pytest tests\test_payloads.py -v`.

### Task 3: Orchestrator Integration

**Files:**
- Modify: `pm_tests/core/orchestrator.py`
- Modify: `tests/test_orchestrator.py`

- [ ] Write an orchestrator test with a fake snapshot adapter returning a long nested string.
- [ ] Confirm the test fails before integration because `case.json` embeds the full string.
- [ ] Call `externalize_large_step_payloads` after each step record is produced.
- [ ] Run `python -m pytest tests\test_orchestrator.py tests\test_payloads.py -v`.

### Task 4: Docs and Verification

**Files:**
- Create: `docs/phase8_artifact_payload_slimming.md`

- [ ] Document the new payload file layout and JSON reference shape.
- [ ] Run `python -m pytest -v`.
- [ ] Run real-device validation if a device is still available.
