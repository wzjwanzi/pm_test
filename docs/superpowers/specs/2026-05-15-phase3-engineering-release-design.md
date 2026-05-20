# Phase 3 Engineering And Release Design

Date: 2026-05-15
Project: mobile_automation_platform

## Context

Phase 1 introduced the typed PM execution core under `pm_tests/core`.
Phase 2 replaced the monolithic desktop UI with a modular `desktop` package while preserving `desktop_app.py` as the executable entrypoint.

The project now needs engineering cleanup so the new source layout is testable, packagable, and easier to operate. Current issues include:

- PyInstaller `build.spec` still references older hidden imports and does not explicitly include the new `desktop.*` and `pm_tests.core.*` modules.
- Runtime dependencies and development/test dependencies are not separated.
- The repository root contains generated logs, caches, build output, release output, and local runtime files.
- Verification commands are known but not captured as reusable scripts.
- The workspace is not a git repository, so changes cannot be committed here.

## Goal

Make the project easier to verify and package after the phase 1 and phase 2 refactors without changing business execution behavior.

## Non-Goals

Phase 3 will not delete existing `release*`, `build_release*`, artifacts, or user-generated logs.

Phase 3 will not run a full PyInstaller build unless explicitly requested after the engineering cleanup, because packaging can be slow and may need environment-specific approval.

Phase 3 will not redesign Web or desktop UI behavior.

Phase 3 will not change PM execution logic except for packaging/import metadata needed by the new modules.

## Packaging Design

Update `build.spec` so packaged desktop builds can discover:

- `desktop`
- `desktop.main`
- `desktop.controller`
- `desktop.state`
- `desktop.formatters`
- `desktop.widgets`
- each module under `desktop.widgets`
- `pm_tests.core`
- each module under `pm_tests.core`

Keep existing Tcl/Tk binaries, Tcl/Tk data, `templates`, `config.py`, and `scrcpy-win64-v2.0` data. Keep `desktop_app.py` as the executable entry script.

## Dependency Design

Keep `requirements.txt` focused on runtime dependencies.

Add `requirements-dev.txt` for local verification dependencies:

- `-r requirements.txt`
- `pytest>=9.0.0`

Do not pin exact versions unless the project already requires strict reproducibility.

## Source Tree Hygiene

Add `.gitignore` to document ignored generated files and local artifacts:

- Python caches and pytest caches.
- Superpowers brainstorming artifacts.
- Build and release directories.
- Runtime settings and logs.
- Temporary stdout/stderr files.
- Generated test run artifacts.

The ignore file documents future cleanup intent, but this phase does not delete existing files.

## Verification Scripts

Add `scripts/verify_dev.ps1` to run:

1. `python -m pytest -v`
2. `python -m py_compile` for key entrypoints and new packages
3. Flask `/api/pm/templates` smoke through `app.test_client()`
4. hidden Tk desktop shell smoke using `desktop_app._prepare_frozen_gui_environment()`

Add `scripts/verify_package.ps1` to run lightweight package checks:

1. Verify `release/MobileTestPlatform/MobileTestPlatform.exe` exists.
2. Start the exe hidden.
3. Wait briefly.
4. Verify the process is still alive or the Flask endpoint responds when available.
5. Stop the process.

The package script should fail with a clear message if no packaged exe exists.

## Documentation

Add `docs/engineering.md` describing:

- Installing runtime dependencies.
- Installing development dependencies.
- Running local verification.
- Building with PyInstaller.
- Running packaged smoke verification.
- The known limitation that this workspace has no git metadata.

## Acceptance Criteria

- `build.spec` includes new desktop and core hidden imports.
- `requirements-dev.txt` exists and includes runtime requirements plus pytest.
- `.gitignore` documents generated/cache/release/runtime files.
- `scripts/verify_dev.ps1` runs the local verification sequence.
- `scripts/verify_package.ps1` checks the packaged exe path without deleting build outputs.
- `docs/engineering.md` explains install, verify, build, and package smoke commands.
- `python -m pytest -v` passes.
- `python -m py_compile app.py desktop_app.py desktop/main.py desktop/controller.py desktop/state.py desktop/formatters.py pm_tests/core/models.py pm_tests/core/facade.py` passes.
