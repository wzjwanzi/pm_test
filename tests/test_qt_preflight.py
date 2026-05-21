from desktop.case_models import CaseStep, SavedCase
from desktop_qt.preflight import Severity, evaluate_case_readiness


def _settings():
    return {
        "base_web": {
            "host": "192.168.13.236",
            "username": "root",
            "password": "web-pass",
            "log_download_dir": r"D:\logs",
        },
        "ssh": {
            "host": "192.168.13.236",
            "username": "root",
            "password": "ssh-pass",
            "rrc_release_command": "release",
            "log_output_dir": r"D:\ssh",
        },
        "traffic": {
            "server_host": "10.88.149.164",
            "server_username": "root",
            "server_password": "traffic-pass",
            "server_downlink_target": "10.6.251.27",
            "server_downlink_port": 6011,
            "server_uplink_listen_port": 7011,
            "phone_uplink_target": "10.88.149.164",
            "phone_uplink_port": 7011,
            "phone_downlink_listen_port": 6011,
            "device_overrides": {"device-1": {"phone_ip": "10.6.251.27"}},
        },
        "common": {"delay_seconds": 5},
    }


def _case(name, actions):
    return SavedCase.new(name, [CaseStep.new(action, action, {}) for action in actions])


def test_downlink_requires_server_target():
    settings = _settings()
    settings["traffic"]["server_downlink_target"] = ""
    case = _case("下行灌包", ["traffic_server_downlink_start"])

    result = evaluate_case_readiness(case, settings, ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is True
    assert "下行灌包缺少服务器下行目标 IP" in result.blocking_messages
    assert any(item.severity == Severity.ERROR for group in result.groups for item in group.items)


def test_bidirectional_passes_when_uplink_and_downlink_are_complete():
    case = _case("双向灌包", ["traffic_server_downlink_start", "phone_uplink_iperf_start"])

    result = evaluate_case_readiness(case, _settings(), ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is False
    assert result.blocking_messages == []


def test_rrc_requires_web_and_ssh_passwords():
    settings = _settings()
    settings["base_web"]["password"] = ""
    settings["ssh"]["password"] = ""
    case = _case("RRC 测试用例", ["base_web_capture_start", "base_ssh_command_start"])

    result = evaluate_case_readiness(case, settings, ["device-1"], {"adb_ok": True}, run_mode="single")

    assert result.blocked is True
    assert "缺少基站 Web 密码" in result.blocking_messages
    assert "缺少基站 SSH 密码" in result.blocking_messages


def test_dual_mode_requires_each_device_phone_ip_mapping():
    settings = _settings()
    case = _case("下行灌包", ["traffic_server_downlink_start"])

    result = evaluate_case_readiness(case, settings, ["device-1", "device-2"], {"adb_ok": True}, run_mode="dual")

    assert result.blocked is True
    assert "双设备模式缺少 device-2 的手机 IP 映射" in result.blocking_messages
