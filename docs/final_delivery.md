# Final Delivery

Date: 2026-05-15

## Delivery Contents

- Refactored PM execution core under `pm_tests/core`.
- Rewritten modular desktop app under `desktop`.
- Thin `desktop_app.py` release entrypoint.
- Engineering verification scripts under `scripts`.
- PyInstaller metadata in `build.spec`.
- Final package target under `release_phase4`.

## Build Command

```powershell
python -m PyInstaller build.spec --clean --noconfirm --distpath release_phase4 --workpath build_phase4
```

## Verification Commands

Development verification:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_dev.ps1
```

Package verification:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe
```

Direct test command:

```powershell
python -m pytest -v
```

## Acceptance Checklist

- `python -m pytest -v` passes.
- `scripts\verify_dev.ps1` passes.
- PyInstaller build creates `release_phase4\MobileTestPlatform\MobileTestPlatform.exe`.
- `scripts\verify_package.ps1` passes for the phase 4 exe.
- Desktop source entrypoint remains `desktop_app.py`.
- Existing `release` directory is not deleted.

## Known Limitation

This workspace has no `.git` directory. Changes cannot be committed, tagged, diffed, or merged with git from this location.
