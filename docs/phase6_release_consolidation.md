# Phase 6 Release Consolidation

Date: 2026-05-15
Project: mobile_automation_platform

## Scope

Phase 6 consolidates the already validated Phase 4 package into a release handoff. It does not rebuild the executable, delete previous release directories, or change application behavior.

## Release Source

- Source package: `release_phase4\MobileTestPlatform`
- Executable: `release_phase4\MobileTestPlatform\MobileTestPlatform.exe`
- Real-device evidence: `artifacts/validation/phase5_real_device_validation.json`

## Release Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_release_bundle.ps1 -Version phase6-20260515
```

## Generated Files

- Release zip: `artifacts/release/MobileTestPlatform-phase6-20260515.zip`
- Release manifest: `artifacts/release/release_manifest.json`

The manifest records:

- release version
- source release directory
- executable path and SHA-256
- zip path and SHA-256
- file count
- Phase 5 validation status
- real device ID
- PM run ID and run status

## Verification Commands

Run the full test suite:

```powershell
python -m pytest -v
```

Verify the packaged executable:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe
```

Optional real-device revalidation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate_real_device.ps1 -DeviceId MKBUT20605024486
```

## Constraints

- This workspace is not a git repository, so release tags and commit hashes are not available.
- The release bundle is file-based and checksum-based.
- Existing `release*` and `build*` directories are preserved.
- Large PM run artifacts are expected because Phase 5 snapshot records include Android `dumpsys` output.
