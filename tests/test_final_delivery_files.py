from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_verifier_accepts_custom_exe_path():
    text = (ROOT / "scripts" / "verify_package.ps1").read_text(encoding="utf-8")

    assert text.lstrip().startswith("param(")
    assert "$ExePath" in text
    assert "MobileTestPlatform.exe" in text


def test_build_scripts_preserve_runtime_settings_and_cases():
    ps_script = (ROOT / "build_release.ps1").read_text(encoding="utf-8")
    build_bat = (ROOT / "build.bat").read_text(encoding="utf-8")
    quick_bat = (ROOT / "quick_build.bat").read_text(encoding="utf-8")

    assert "settings.json" in ps_script
    assert "release\\MobileTestPlatform\\settings.json" in ps_script
    assert "release\\MobileTestPlatform\\cases" in ps_script
    assert "settings.json" in build_bat
    assert "release\\MobileTestPlatform\\settings.json" in build_bat
    assert "release\\MobileTestPlatform\\cases" in build_bat
    assert "settings.json" in quick_bat
    assert "release\\MobileTestPlatform\\settings.json" in quick_bat
    assert "release\\MobileTestPlatform\\cases" in quick_bat


def test_final_delivery_docs_include_required_commands():
    quick_start = (ROOT / "docs" / "user_quick_start.md").read_text(encoding="utf-8")
    final_delivery = (ROOT / "docs" / "final_delivery.md").read_text(encoding="utf-8")

    assert "desktop_app.py" in quick_start
    assert "release_phase4" in final_delivery
    assert "verify_dev.ps1" in final_delivery
    assert "verify_package.ps1" in final_delivery
    assert "PyInstaller" in final_delivery
