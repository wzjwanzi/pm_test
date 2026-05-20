# Engineering Guide

This project has a Flask API, a Tkinter desktop entrypoint, PM execution modules, and PyInstaller packaging.

## Runtime Install

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Development Install

Install runtime plus test dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes `pytest` and references the runtime dependency file.

## Local Verification

Run the full local verification script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_dev.ps1
```

The script runs:

- `python -m pytest -v`
- Python compile checks for app, desktop, widgets, and PM core modules
- Flask `/api/pm/templates` smoke check
- hidden Tk desktop shell smoke check

## Manual Test Commands

```powershell
python -m pytest -v
```

```powershell
python -m py_compile app.py desktop_app.py desktop/main.py desktop/controller.py desktop/state.py desktop/formatters.py pm_tests/core/models.py pm_tests/core/facade.py
```

## Build

Build with the existing PyInstaller spec:

```powershell
python -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release
```

The spec keeps `desktop_app.py` as the executable entrypoint and includes the `desktop.*` and `pm_tests.core.*` packages in hidden imports.

## Packaged Smoke

After a package exists at `release\MobileTestPlatform\MobileTestPlatform.exe`, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1
```

The package smoke script starts the exe hidden, verifies it remains alive briefly, and stops it.

## Git Limitation

This workspace currently has no `.git` directory, so local changes cannot be committed, branched, or diffed with git commands here.
