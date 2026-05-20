from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_bundle_script_captures_manifest_contract():
    script = ROOT / "scripts" / "create_release_bundle.ps1"

    assert script.exists()

    text = script.read_text(encoding="utf-8")
    assert "[string]$ReleaseDir" in text
    assert "[string]$OutputDir" in text
    assert "[string]$Version" in text
    assert "[string]$ValidationJson" in text
    assert "MobileTestPlatform.exe" in text
    assert "Compress-Archive" in text
    assert "Get-FileHash" in text
    assert "release_manifest.json" in text
    assert "phase5_real_device_validation.json" in text
    assert "run_id" in text
    assert "run_status" in text


def test_phase6_release_report_documents_handoff_evidence():
    report = ROOT / "docs" / "phase6_release_consolidation.md"

    assert report.exists()

    text = report.read_text(encoding="utf-8")
    assert "MobileTestPlatform-phase6-20260515.zip" in text
    assert "artifacts/release/release_manifest.json" in text
    assert "artifacts/validation/phase5_real_device_validation.json" in text
    assert "scripts\\verify_package.ps1" in text
    assert "release_phase4\\MobileTestPlatform\\MobileTestPlatform.exe" in text


def test_no_flask_or_web_templates_are_packaged():
    assert not (ROOT / "templates").exists()
    assert "Flask" not in (ROOT / "requirements.txt").read_text(encoding="utf-8")
    build_text = (ROOT / "build.spec").read_text(encoding="utf-8")
    assert "templates/index.html" not in build_text
    assert "('templates'" not in build_text


def test_no_appium_imports_in_execution_path():
    execution_files = [
        ROOT / "desktop" / "controller.py",
        ROOT / "pm_tests" / "core" / "planner.py",
        ROOT / "pm_tests" / "core" / "adapters.py",
        ROOT / "pm_tests" / "core" / "facade.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in execution_files)
    assert "appium" not in combined.lower()
