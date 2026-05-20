import copy
import tkinter as tk
from types import SimpleNamespace

import pytest

import config
from app_settings import (
    build_device_traffic_iperf_command,
    load_runtime_settings,
    normalize_runtime_settings,
    save_runtime_settings,
    save_runtime_settings_group,
)
from desktop.settings_forms import (
    SettingsValidationError,
    extract_business_modules,
    merge_business_module,
)


def test_save_runtime_settings_group_updates_one_group_without_overwriting_others(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    initial = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    initial["traffic"]["server_host"] = "10.88.149.164"
    initial["traffic"]["server_password"] = "traffic-pass"
    initial["base_web"]["host"] = "192.168.13.236"
    save_runtime_settings(initial)

    saved = save_runtime_settings_group(
        "base_web",
        {
            "host": "192.168.13.250",
            "port": 8400,
            "username": "root",
            "password": "web-pass",
            "log_download_dir": r"D:\web_logs",
        },
    )
    reloaded = load_runtime_settings()

    assert saved["base_web"]["host"] == "192.168.13.250"
    assert reloaded["base_web"]["password"] == "web-pass"
    assert reloaded["traffic"]["server_host"] == "10.88.149.164"
    assert reloaded["traffic"]["server_password"] == "traffic-pass"


def test_save_runtime_settings_group_rejects_unknown_group(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")

    with pytest.raises(KeyError):
        save_runtime_settings_group("unknown", {})


def test_settings_file_follows_runtime_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RUNTIME_DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")

    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["base_web"]["host"] = "192.168.13.250"
    save_runtime_settings(settings)

    assert (tmp_path / "settings.json").exists()
    assert load_runtime_settings()["base_web"]["host"] == "192.168.13.250"


def test_extract_business_modules_groups_runtime_settings_by_business_area():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["base_web"]["password"] = "web-pass"
    settings["ssh"]["password"] = "ssh-pass"
    settings["traffic"]["server_password"] = "server-pass"
    settings["iperf"]["host"] = "10.0.0.9"
    settings["ping"]["host"] = "10.0.0.10"
    settings["traffic"]["phone_uplink_target"] = "10.0.0.11"
    settings["common"]["delay_seconds"] = 30

    modules = extract_business_modules(settings)

    assert modules["base_web"]["password"] == "web-pass"
    assert modules["ssh"]["password"] == "ssh-pass"
    assert modules["traffic_server"]["server_password"] == "server-pass"
    assert modules["phone"]["iperf.host"] == "10.0.0.9"
    assert modules["phone"]["ping.host"] == "10.0.0.10"
    assert modules["phone"]["traffic.phone_uplink_target"] == "10.0.0.11"
    assert modules["common"]["delay_seconds"] == 30


def test_ssh_runtime_config_exposes_rrc_log_commands():
    from desktop.settings_forms import MODULE_FIELDS

    field_keys = [field.key for field in MODULE_FIELDS["ssh"]]
    normalized = normalize_runtime_settings({"ssh": {}})

    assert "log_command" not in field_keys
    assert "rlc_up_log_command" in field_keys
    assert "rate_log_command" in field_keys
    assert "cpu_log_command" in field_keys
    assert "rrc_release_command" in field_keys
    assert "rrc_release_count" in field_keys
    assert "rrc_release_interval_seconds" in field_keys
    assert "force_rlc_escape_command" in field_keys
    assert "force_rlc_escape_count" in field_keys
    assert "force_rlc_escape_interval_seconds" in field_keys
    assert normalized["ssh"]["log_command"] == ""
    assert "dump-rlc-om-info" in normalized["ssh"]["rlc_up_log_command"]
    assert "show-mac-throughput-count" in normalized["ssh"]["rate_log_command"]
    assert "top -b -n 1" in normalized["ssh"]["cpu_log_command"]
    assert "release-ue" in normalized["ssh"]["rrc_release_command"]
    assert normalized["ssh"]["rrc_release_count"] == 8
    assert normalized["ssh"]["rrc_release_interval_seconds"] == 5
    assert "force-rlc-escape-ctrl" in normalized["ssh"]["force_rlc_escape_command"]
    assert normalized["ssh"]["force_rlc_escape_count"] == 3
    assert normalized["ssh"]["force_rlc_escape_interval_seconds"] == 5


def test_merge_base_web_module_preserves_other_business_modules():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["ssh"]["host"] = "10.88.149.164"
    settings["traffic"]["server_host"] = "10.88.149.200"
    settings["iperf"]["host"] = "10.88.149.201"

    merged = merge_business_module(
        settings,
        "base_web",
        {
            "host": "192.168.13.250",
            "port": "8500",
            "username": "web-user",
            "password": "plain-password",
            "log_download_dir": r"D:\web_logs",
            "capture_signal_enabled": True,
            "capture_data_enabled": False,
            "capture_fapi_interface": "FAPI3",
        },
    )

    assert merged["base_web"]["host"] == "192.168.13.250"
    assert merged["base_web"]["port"] == 8500
    assert merged["base_web"]["password"] == "plain-password"
    assert merged["ssh"]["host"] == "10.88.149.164"
    assert merged["traffic"]["server_host"] == "10.88.149.200"
    assert merged["iperf"]["host"] == "10.88.149.201"


def test_base_web_runtime_config_allows_no_fapi_choice():
    from desktop.settings_forms import MODULE_FIELDS

    fapi_field = next(field for field in MODULE_FIELDS["base_web"] if field.key == "capture_fapi_interface")

    merged = merge_business_module(
        copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS),
        "base_web",
        {"capture_fapi_interface": "无"},
    )
    normalized = normalize_runtime_settings(merged)

    assert fapi_field.choices == ("无", "FAPI1", "FAPI3")
    assert normalized["base_web"]["capture_fapi_interface"] == "无"
    assert normalized["base_web"]["capture_transmit_ip"] == ""


def test_merge_traffic_server_module_preserves_phone_traffic_fields():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    settings["traffic"]["phone_uplink_target"] = "10.0.0.11"
    settings["traffic"]["phone_downlink_listen_port"] = 6011

    merged = merge_business_module(
        settings,
        "traffic_server",
        {
            "server_host": "10.88.149.210",
            "server_port": "22",
            "server_username": "root",
            "server_password": "server-pass",
            "server_connect_timeout": "30",
            "server_log_dir": r"D:\server_logs",
            "server_downlink_target": "10.6.250.12",
            "server_downlink_port": "6012",
            "server_downlink_bandwidth": "300m",
            "server_downlink_duration": "5000",
            "server_downlink_packet_len": "1300",
            "server_uplink_listen_port": "7012",
            "server_ping_target": "10.6.250.1",
            "server_ping_count": "0",
        },
    )

    assert merged["traffic"]["server_host"] == "10.88.149.210"
    assert merged["traffic"]["server_downlink_port"] == 6012
    assert merged["traffic"]["server_ping_count"] == 0
    assert merged["traffic"]["phone_uplink_target"] == "10.0.0.11"
    assert merged["traffic"]["phone_downlink_listen_port"] == 6011


def test_traffic_server_runtime_config_exposes_ping_count_allowing_zero():
    from app_settings import normalize_runtime_settings
    from desktop.settings_forms import MODULE_FIELDS

    field_keys = [field.key for field in MODULE_FIELDS["traffic_server"]]
    normalized = normalize_runtime_settings({"traffic": {"server_ping_count": "0"}})

    assert "server_ping_count" in field_keys
    assert normalized["traffic"]["server_ping_count"] == 0


def test_merge_phone_module_updates_iperf_ping_and_phone_traffic_fields():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    merged = merge_business_module(
        settings,
        "phone",
        {
            "iperf.tool": "iperf",
            "iperf.host": "10.88.149.220",
            "iperf.port": "6088",
            "iperf.bandwidth": "150m",
            "iperf.duration": "6000",
            "iperf.interval": "2",
            "iperf.packet_len": "1200",
            "iperf.protocol": "tcp",
            "ping.host": "10.88.149.221",
            "ping.count": "6",
            "traffic.phone_uplink_target": "10.88.149.222",
            "traffic.phone_uplink_port": "7013",
            "traffic.phone_uplink_bandwidth": "110m",
            "traffic.phone_uplink_duration": "7000",
            "traffic.phone_uplink_packet_len": "1250",
            "traffic.phone_downlink_listen_port": "6013",
            "traffic.phone_ping_target": "10.88.149.223",
        },
    )

    assert merged["iperf"]["tool"] == "iperf"
    assert merged["iperf"]["port"] == 6088
    assert merged["ping"]["host"] == "10.88.149.221"
    assert merged["ping"]["count"] == 6
    assert merged["traffic"]["phone_uplink_target"] == "10.88.149.222"
    assert merged["traffic"]["phone_downlink_listen_port"] == 6013


def test_merge_common_module_updates_delay_seconds():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    merged = merge_business_module(settings, "common", {"delay_seconds": "45"})
    normalized = normalize_runtime_settings(merged)

    assert normalized["common"]["delay_seconds"] == 45


def test_merge_business_module_rejects_invalid_integer_before_persistence():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    with pytest.raises(SettingsValidationError) as exc:
        merge_business_module(settings, "ssh", {"port": "not-a-number"})

    assert "port" in str(exc.value)


def test_merge_business_module_rejects_invalid_choice_before_persistence():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    with pytest.raises(SettingsValidationError) as exc:
        merge_business_module(settings, "phone", {"iperf.protocol": "sctp"})

    assert "iperf.protocol" in str(exc.value)


def test_merge_business_module_rejects_invalid_bool_string_before_persistence():
    settings = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    with pytest.raises(SettingsValidationError) as exc:
        merge_business_module(settings, "base_web", {"capture_signal_enabled": "maybe"})

    assert "capture_signal_enabled" in str(exc.value)


def test_device_traffic_iperf_command_is_displayed_as_adb_shell_command(monkeypatch):
    monkeypatch.setattr("app_settings.get_device_iperf_binary", lambda: "/data/local/tmp/iperf")

    assert build_device_traffic_iperf_command("-u -s -i 1 -p 6011") == (
        "adb shell /data/local/tmp/iperf -u -s -i 1 -p 6011"
    )


def test_settings_panel_uses_business_module_definitions():
    from desktop.settings_forms import MODULE_FIELDS, MODULE_LABELS
    from desktop.widgets.settings import SettingsPanel

    assert SettingsPanel is not None
    assert list(MODULE_FIELDS) == ["base_web", "ssh", "traffic_server", "phone", "common"]
    assert MODULE_LABELS["traffic_server"] == "灌包服务器"
    assert MODULE_LABELS["common"] == "通用"


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display is not available: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


class _PanelController:
    def __init__(self):
        self.reset_calls = 0
        self.save_calls = 0

    def load_settings(self):
        return copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)

    def save_settings(self, settings):
        self.save_calls += 1
        return settings

    def reset_settings(self):
        self.reset_calls += 1
        return copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)


def _make_settings_panel(root):
    from desktop.widgets.settings import SettingsPanel

    controller = _PanelController()
    app = SimpleNamespace(
        controller=controller,
        messages=[],
        set_message=lambda message: app.messages.append(message),
    )
    panel = SettingsPanel(root, app)
    panel.pack()
    return panel, controller


def test_settings_panel_set_module_values_defaults_missing_bool(tk_root):
    panel, _controller = _make_settings_panel(tk_root)

    panel._set_module_values("base_web", {})

    assert panel.field_vars["base_web"]["capture_signal_enabled"].get() is False
    assert panel.field_vars["base_web"]["capture_data_enabled"].get() is False


def test_settings_panel_reset_cancel_does_not_call_reset_settings(monkeypatch, tk_root):
    from desktop.widgets import settings as settings_widget

    panel, controller = _make_settings_panel(tk_root)
    monkeypatch.setattr(settings_widget.messagebox, "askyesno", lambda *args, **kwargs: False)

    panel.reset()

    assert controller.reset_calls == 0


def test_settings_panel_save_group_validation_prevents_save_settings(monkeypatch, tk_root):
    from desktop.widgets import settings as settings_widget

    panel, controller = _make_settings_panel(tk_root)
    errors = []
    monkeypatch.setattr(settings_widget.messagebox, "showerror", lambda *args, **kwargs: errors.append(args))
    panel.field_vars["ssh"]["port"].set("not-a-number")

    panel.save_group("ssh")

    assert controller.save_calls == 0
    assert errors


def test_settings_panel_load_controller_error_shows_message(monkeypatch, tk_root):
    from desktop.widgets import settings as settings_widget

    panel, _controller = _make_settings_panel(tk_root)
    errors = []
    panel.app.controller.load_settings = lambda: (_ for _ in ()).throw(RuntimeError("load failed"))
    monkeypatch.setattr(settings_widget.messagebox, "showerror", lambda *args, **kwargs: errors.append(args))

    panel.load()

    assert errors
    assert "load failed" in errors[0][1]
