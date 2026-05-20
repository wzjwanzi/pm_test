from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_verifier_accepts_custom_exe_path():
    text = (ROOT / "scripts" / "verify_package.ps1").read_text(encoding="utf-8")

    assert text.lstrip().startswith("param(")
    assert "$ExePath" in text
    assert "MobileTestPlatform.exe" in text


def test_final_delivery_docs_include_required_commands():
    quick_start = (ROOT / "docs" / "user_quick_start.md").read_text(encoding="utf-8")
    final_delivery = (ROOT / "docs" / "final_delivery.md").read_text(encoding="utf-8")

    assert "desktop_app.py" in quick_start
    assert "release_phase4" in final_delivery
    assert "verify_dev.ps1" in final_delivery
    assert "verify_package.ps1" in final_delivery
    assert "PyInstaller" in final_delivery
