# Phase 3 Engineering And Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the refactored project verifiable and packagable by updating release metadata, dependency files, hygiene rules, verification scripts, and engineering docs.

**Architecture:** Keep runtime code unchanged. Add engineering files and update `build.spec` hidden imports so the phase 1 core and phase 2 desktop packages are included by PyInstaller.

**Tech Stack:** Python 3.11, PyInstaller spec syntax, PowerShell verification scripts, pytest.

---

## File Structure

- Modify `build.spec`: add `desktop.*` and `pm_tests.core.*` hidden imports.
- Create `.gitignore`: ignore generated caches, build/release output, runtime logs/settings, and local artifacts.
- Create `requirements-dev.txt`: include runtime requirements and pytest.
- Create `scripts/verify_dev.ps1`: local test/compile/smoke verification.
- Create `scripts/verify_package.ps1`: packaged exe smoke verification.
- Create `docs/engineering.md`: install, verify, build, package smoke instructions.
- Create `tests/test_engineering_files.py`: assert engineering files contain required entries.

## Task 1: Engineering File Tests

**Files:**
- Create: `tests/test_engineering_files.py`

- [ ] **Step 1: Write failing tests**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_spec_includes_refactored_packages():
    text = (ROOT / "build.spec").read_text(encoding="utf-8")

    for name in [
        "desktop",
        "desktop.main",
        "desktop.widgets.devices",
        "desktop.widgets.cases",
        "desktop.widgets.run_monitor",
        "desktop.widgets.results",
        "desktop.widgets.settings",
        "pm_tests.core",
        "pm_tests.core.facade",
        "pm_tests.core.orchestrator",
        "pm_tests.core.adapters",
    ]:
        assert repr(name) in text


def test_engineering_files_exist_and_cover_expected_commands():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    dev_requirements = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    verify_dev = (ROOT / "scripts" / "verify_dev.ps1").read_text(encoding="utf-8")
    verify_package = (ROOT / "scripts" / "verify_package.ps1").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "engineering.md").read_text(encoding="utf-8")

    assert "__pycache__/" in gitignore
    assert "release*/" in gitignore
    assert "desktop_app.log" in gitignore
    assert "-r requirements.txt" in dev_requirements
    assert "pytest" in dev_requirements
    assert "python -m pytest -v" in verify_dev
    assert "desktop_app._prepare_frozen_gui_environment()" in verify_dev
    assert "MobileTestPlatform.exe" in verify_package
    assert "requirements-dev.txt" in docs
    assert "verify_dev.ps1" in docs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_engineering_files.py -v`

Expected: FAIL because the new engineering files and hidden imports are not present.

## Task 2: Packaging Metadata And Hygiene Files

**Files:**
- Modify: `build.spec`
- Create: `.gitignore`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Update `build.spec` hidden imports**

Add the required new hidden imports in the existing `hiddenimports` list.

- [ ] **Step 2: Add `.gitignore`**

Include ignores for Python caches, pytest cache, `.superpowers/`, build/release directories, logs, `settings.json`, stdout/stderr logs, and artifacts.

- [ ] **Step 3: Add `requirements-dev.txt`**

Content:

```text
-r requirements.txt
pytest>=9.0.0
```

- [ ] **Step 4: Run engineering file tests**

Run: `python -m pytest tests/test_engineering_files.py -v`

Expected: FAIL until scripts and docs are added; build spec and dependency assertions should pass.

## Task 3: Verification Scripts And Engineering Docs

**Files:**
- Create: `scripts/verify_dev.ps1`
- Create: `scripts/verify_package.ps1`
- Create: `docs/engineering.md`

- [ ] **Step 1: Add `scripts/verify_dev.ps1`**

Script must run tests, compile checks, Flask smoke, and hidden Tk smoke. Use `$ErrorActionPreference = 'Stop'`.

- [ ] **Step 2: Add `scripts/verify_package.ps1`**

Script must check `release/MobileTestPlatform/MobileTestPlatform.exe`, start it hidden, wait briefly, report process state, and stop it.

- [ ] **Step 3: Add `docs/engineering.md`**

Document install, dev install, local verification, build, package smoke, and no-git limitation.

- [ ] **Step 4: Run engineering file tests**

Run: `python -m pytest tests/test_engineering_files.py -v`

Expected: PASS.

## Task 4: Full Verification

**Files:**
- Modify only files needed by verification failures.

- [ ] **Step 1: Run all tests**

Run: `python -m pytest -v`

Expected: PASS.

- [ ] **Step 2: Run compile smoke**

Run: `python -m py_compile app.py desktop_app.py desktop/main.py desktop/controller.py desktop/state.py desktop/formatters.py pm_tests/core/models.py pm_tests/core/facade.py`

Expected: no output and exit code 0.

- [ ] **Step 3: Run development verification script**

Run: `powershell -ExecutionPolicy Bypass -File scripts\\verify_dev.ps1`

Expected: tests pass, compile pass, Flask smoke prints `200` and `True`, Tk smoke prints `panels= True`.

- [ ] **Step 4: Do not run package verification unless exe exists**

If `release\\MobileTestPlatform\\MobileTestPlatform.exe` exists, run:

`powershell -ExecutionPolicy Bypass -File scripts\\verify_package.ps1`

Expected: reports the exe path and exits 0 after stopping the process.

- [ ] **Step 5: Document git limitation**

Because this workspace has no `.git` directory, do not run commit steps. Record changed files and verification output in the final response.
