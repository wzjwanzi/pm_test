from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_spec_includes_refactored_packages():
    text = (ROOT / "build.spec").read_text(encoding="utf-8")

    for name in [
        "desktop",
        "desktop.controller",
        "desktop.case_templates",
        "desktop_qt.main_window",
        "desktop_qt.pages.home",
        "desktop_qt.pages.case_library",
        "desktop_qt.pages.settings",
        "pm_tests.core",
        "pm_tests.core.facade",
        "pm_tests.core.orchestrator",
        "pm_tests.core.adapters",
    ]:
        assert repr(name) in text
    assert "desktop.main" not in text
    assert "desktop.widgets" not in text
    assert "tkinter" not in text.lower()


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
    assert "desktop_qt.main_window" in verify_dev
    assert "MobileTestPlatform.exe" in verify_package
    assert "requirements-dev.txt" in docs
    assert "verify_dev.ps1" in docs
