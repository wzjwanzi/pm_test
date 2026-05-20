# Phase 7 Result Handoff

Date: 2026-05-15
Project: mobile_automation_platform

## Scope

Phase 7 adds desktop result handoff actions for completed runs. It does not change PM execution behavior or rewrite existing run artifacts.

## Desktop Actions

The results panel now exposes:

- Export report: writes a compact Markdown summary named `run_report.md`.
- Open artifacts: opens the selected run's artifact directory.

## Report Location

By default, report export writes to the selected run artifact directory:

```text
artifacts/test_runs/<run-id>/run_report.md
```

The report includes run metadata, summary counts, artifact path, and step rows. It intentionally avoids embedding the full raw `run.json` payload because real-device snapshots can include large Android `dumpsys` output.

## Validation

Developer verification:

```powershell
python -m pytest tests\test_desktop_artifacts.py tests\test_desktop_controller.py tests\test_desktop_shell.py -v
python -m pytest -v
```

Packaged executable verification:

```powershell
python -m PyInstaller build.spec --clean --noconfirm --distpath release_phase7 --workpath build_phase7
powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase7\MobileTestPlatform\MobileTestPlatform.exe
powershell -ExecutionPolicy Bypass -File scripts\create_release_bundle.ps1 -ReleaseDir release_phase7\MobileTestPlatform -Version phase7-20260515
```

Generated package:

- `release_phase7\MobileTestPlatform\MobileTestPlatform.exe`
- `artifacts/release/MobileTestPlatform-phase7-20260515.zip`
- `artifacts/release/release_manifest.json`

Manual desktop verification:

1. Start the desktop app.
2. Select or create a run with an artifact directory.
3. Use Export report.
4. Confirm `run_report.md` appears in the run artifact directory.
5. Use Open artifacts.
6. Confirm the artifact directory opens in Windows Explorer.

## Constraints

- Opening artifact directories is implemented for Windows desktop usage.
- Missing or deleted artifact directories are reported as user-visible messages.
- Existing `run.json` and `case.json` files remain unchanged.
