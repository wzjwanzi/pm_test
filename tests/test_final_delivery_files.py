from pathlib import Path
import json
import copy


ROOT = Path(__file__).resolve().parents[1]


def test_package_verifier_accepts_custom_exe_path():
    text = (ROOT / "scripts" / "verify_package.ps1").read_text(encoding="utf-8")

    assert text.lstrip().startswith("param(")
    assert "$ExePath" in text
    assert "MobileTestPlatform.exe" in text


def test_build_scripts_preserve_runtime_settings_without_saved_case_overrides():
    ps_script = (ROOT / "build_release.ps1").read_text(encoding="utf-8")
    build_bat = (ROOT / "build.bat").read_text(encoding="utf-8")
    quick_bat = (ROOT / "quick_build.bat").read_text(encoding="utf-8")

    assert "settings.json" in ps_script
    assert "release\\MobileTestPlatform\\settings.json" in ps_script
    assert "Copy-Item -LiteralPath $casesSource" not in ps_script
    assert "settings.json" in build_bat
    assert "release\\MobileTestPlatform\\settings.json" in build_bat
    assert "xcopy /E /I /Y cases" not in build_bat
    assert "settings.json" in quick_bat
    assert "release\\MobileTestPlatform\\settings.json" in quick_bat
    assert "xcopy /E /I /Y cases" not in quick_bat


def test_build_script_validates_release_settings_match_source_settings():
    ps_script = (ROOT / "build_release.ps1").read_text(encoding="utf-8")

    assert "Assert-ReleaseSettingsMatchesSource" in ps_script
    assert "traffic.server_host" in ps_script
    assert "settings.json mismatch after packaging" in ps_script


def test_packaged_runtime_settings_use_traffic_server_ssh_ip():
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))

    assert settings["traffic"]["server_host"] == "192.168.13.164"


def test_device_runtime_settings_use_phone_reachable_traffic_server_ip():
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    overrides = settings["traffic"]["device_overrides"]

    for values in overrides.values():
        assert values["traffic_server_ip"] == "10.88.149.164"
        assert values["phone_uplink_target"] == "10.88.149.164"
        assert values["phone_ping_target"] == "10.88.149.164"


def test_runtime_settings_follow_mobile_platform_config_template():
    import config
    from app_settings import normalize_runtime_settings

    template = json.loads((ROOT / "mobile_platform_config.json").read_text(encoding="utf-8"))
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    normalized_template = normalize_runtime_settings(template)

    assert settings == normalized_template
    assert settings["base_web"]["capture_fapi_interface"] == "无"
    assert settings["base_web"]["capture_transmit_ip"] == ""
    assert settings["traffic"]["device_overrides"]["MKBUT20508005446"]["phone_ip"] == "10.6.251.20"
    assert Path(config.BUILTIN_CONFIG_TEMPLATE_FILE).name == "mobile_platform_config.json"


def test_root_runtime_settings_match_builtin_default_template():
    import config
    from app_settings import normalize_runtime_settings

    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    defaults = normalize_runtime_settings(copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS))

    assert settings == defaults


def test_final_delivery_docs_include_required_commands():
    quick_start = (ROOT / "docs" / "user_quick_start.md").read_text(encoding="utf-8")
    final_delivery = (ROOT / "docs" / "final_delivery.md").read_text(encoding="utf-8")

    assert "desktop_app.py" in quick_start
    assert "release_phase4" in final_delivery
    assert "verify_dev.ps1" in final_delivery
    assert "verify_package.ps1" in final_delivery
    assert "PyInstaller" in final_delivery
