from desktop.case_models import SavedCase
from desktop.case_templates import ACTIONS, build_default_case_templates, remap_case_params_from_settings, step_from_template


def test_actions_include_base_web_ssh_server_and_phone_options():
    ids = {item.action for item in ACTIONS}

    assert "base_web_capture_start" in ids
    assert "base_web_capture_stop" in ids
    assert "base_ssh_log_start" in ids
    assert "traffic_server_downlink_start" in ids
    assert "traffic_server_downlink_stop" in ids
    assert "phone_uplink_iperf_start" in ids
    assert "phone_uplink_iperf_stop" in ids
    assert "phone_airplane_mode_off" in ids
    assert "phone_airplane_mode_on" in ids
    assert "phone_airplane_cycle" in ids
    assert "common_delay" in ids
    assert "base_ssh_command_start" in ids
    assert "base_ssh_command_stop" in ids
    assert "base_ssh_command_repeat" in ids
    assert "base_ssh_rlc_up_log_start" in ids
    assert "base_ssh_rate_log_start" in ids
    assert "base_ssh_cpu_log_start" in ids
    assert "base_ssh_rrc_release_repeat" in ids
    assert "base_ssh_force_rlc_escape_repeat" in ids


def test_step_copies_runtime_defaults_without_mutating_settings():
    settings = {
        "base_url": "http://192.168.13.236:8400",
        "base_username": "root",
        "base_password": "5GNR@root",
        "traffic_server_host": "10.88.149.164",
        "traffic_server_user": "root",
        "traffic_server_password": "Root@164_",
        "iperf_port": 7011,
        "iperf_bandwidth": "100M",
        "iperf_duration": 60,
        "download_dir": "D:\\test\\autopm_system\\log",
    }

    step = step_from_template("traffic_server_downlink_start", settings)
    step.params["server_host"] = "1.1.1.1"

    assert step.params["server_host"] == "1.1.1.1"
    assert settings["traffic_server_host"] == "10.88.149.164"


def test_base_web_capture_defaults_to_no_fapi_option():
    from desktop.case_templates import ACTION_BY_ID

    step = step_from_template("base_web_capture_start", {})
    fapi_field = next(
        field
        for field in ACTION_BY_ID["base_web_capture_start"].fields
        if field["name"] == "capture_fapi_interface"
    )

    assert step.params["capture_fapi_interface"] == "无"
    assert fapi_field["choices"] == ["无", "FAPI1", "FAPI3"]


def test_base_station_steps_do_not_include_traffic_parameters():
    for action in ("base_web_capture_start", "base_web_capture_stop", "base_web_collect_log", "base_ssh_log_start"):
        step = step_from_template(action, {})

        assert "iperf_port" not in step.params
        assert "iperf_bandwidth" not in step.params
        assert "iperf_duration" not in step.params
        assert "server_host" not in step.params


def test_base_web_and_ssh_steps_use_separate_credentials_and_ssh_port():
    settings = {
        "base_web": {
            "host": "192.168.13.236",
            "port": 8400,
            "username": "web_user",
            "password": "web_password",
            "log_download_dir": "D:\\web_logs",
        },
        "ssh": {
            "host": "10.88.149.164",
            "port": 22,
            "username": "ssh_user",
            "password": "ssh_password",
            "log_output_dir": "D:\\ssh_logs",
            "log_command": "tail -f /tmp/base.log",
        },
    }

    web_step = step_from_template("base_web_capture_start", settings)
    ssh_step = step_from_template("base_ssh_log_start", settings)

    assert web_step.params["web_username"] == "web_user"
    assert web_step.params["web_password"] == "web_password"
    assert "ssh_password" not in web_step.params
    assert ssh_step.params["ssh_host"] == "10.88.149.164"
    assert ssh_step.params["ssh_port"] == 22
    assert ssh_step.params["ssh_username"] == "ssh_user"
    assert ssh_step.params["ssh_password"] == "ssh_password"
    assert "web_password" not in ssh_step.params
    assert "base_password" not in ssh_step.params


def test_base_ssh_business_steps_use_configured_commands():
    settings = {
        "ssh": {
            "host": "10.88.149.164",
            "port": 22,
            "username": "root",
            "password": "Root@164_",
            "log_output_dir": r"D:\test\mobile_automation_platform\ssh_log",
            "rlc_up_log_command": "custom rlc",
            "rate_log_command": "custom rate",
            "cpu_log_command": "custom cpu",
            "rrc_release_command": "custom release",
            "rrc_release_count": 8,
            "rrc_release_interval_seconds": 5,
            "force_rlc_escape_command": "custom force",
            "force_rlc_escape_count": 3,
            "force_rlc_escape_interval_seconds": 7,
        }
    }

    rlc = step_from_template("base_ssh_rlc_up_log_start", settings)
    rate = step_from_template("base_ssh_rate_log_start", settings)
    cpu = step_from_template("base_ssh_cpu_log_start", settings)
    release = step_from_template("base_ssh_rrc_release_repeat", settings)
    force = step_from_template("base_ssh_force_rlc_escape_repeat", settings)
    stop = step_from_template("base_ssh_cpu_log_stop", settings)

    assert rlc.action == "base_ssh_rlc_up_log_start"
    assert rlc.label.endswith("开始 RLC/UP 日志")
    assert rlc.params["command"] == "custom rlc"
    assert rlc.params["session_key"] == "rrc_rlc_up"
    assert rate.params["command"] == "custom rate"
    assert rate.params["session_key"] == "rrc_rate"
    assert cpu.params["command"] == "custom cpu"
    assert cpu.params["session_key"] == "rrc_cpu"
    assert release.params["command"] == "custom release"
    assert release.params["repeat_count"] == 8
    assert release.params["interval_seconds"] == 5
    assert force.params["command"] == "custom force"
    assert force.params["repeat_count"] == 3
    assert force.params["interval_seconds"] == 7
    assert stop.action == "base_ssh_cpu_log_stop"
    assert stop.params["session_key"] == "rrc_cpu"


def test_base_station_ip_does_not_drive_traffic_server_ip():
    settings = {
        "base_web": {"host": "192.168.13.236", "port": 8400},
        "ssh": {"host": "192.168.13.237", "port": 22},
        "traffic": {
            "server_host": "10.88.149.164",
            "server_username": "traffic_user",
            "server_password": "traffic_password",
        },
    }

    web_step = step_from_template("base_web_capture_start", settings)
    ssh_step = step_from_template("base_ssh_log_start", settings)
    traffic_step = step_from_template("traffic_server_downlink_start", settings)

    assert web_step.params["web_host"] == "192.168.13.236"
    assert ssh_step.params["ssh_host"] == "192.168.13.237"
    assert traffic_step.params["server_host"] == "10.88.149.164"
    assert traffic_step.params["server_user"] == "traffic_user"
    assert traffic_step.params["server_password"] == "traffic_password"
    assert traffic_step.params["server_host"] != web_step.params["web_host"]
    assert traffic_step.params["server_host"] != ssh_step.params["ssh_host"]


def test_traffic_ping_steps_do_not_include_iperf_bandwidth_parameters():
    step = step_from_template("traffic_server_down_ping_start", {"traffic_server_host": "10.88.149.164"})

    assert step.params["server_host"] == "10.88.149.164"
    assert "iperf_bandwidth" not in step.params
    assert "iperf_duration" not in step.params
    assert "iperf_port" not in step.params


def test_phone_airplane_steps_have_expected_runtime_parameters():
    off_step = step_from_template("phone_airplane_mode_off", {})
    on_step = step_from_template("phone_airplane_mode_on", {})
    cycle_step = step_from_template("phone_airplane_cycle", {})

    assert off_step.label.endswith("关闭飞行模式入网")
    assert on_step.label.endswith("开启飞行模式脱网")
    assert off_step.params == {}
    assert on_step.params == {}
    assert cycle_step.label.endswith("飞行操作")
    assert cycle_step.params == {"detach_wait_seconds": 5, "attach_wait_seconds": 5}


def test_common_delay_step_has_configurable_seconds():
    step = step_from_template("common_delay", {"common": {"delay_seconds": 12}})

    assert step.label.endswith("延时")
    assert step.params == {"delay_seconds": 12}


def test_traffic_ping_step_uses_configured_ping_count_zero_for_continuous_ping():
    step = step_from_template(
        "traffic_server_down_ping_start",
        {"traffic": {"server_ping_target": "10.6.250.2", "server_ping_count": 0}},
    )

    assert step.params["ping_target"] == "10.6.250.2"
    assert step.params["ping_count"] == 0


def test_traffic_iperf_steps_keep_bandwidth_parameters():
    step = step_from_template("traffic_server_downlink_start", {"iperf_bandwidth": "250M"})

    assert step.params["iperf_bandwidth"] == "250M"
    assert "server_host" in step.params


def test_traffic_server_iperf_steps_include_generated_commands():
    settings = {
        "traffic": {
            "server_downlink_target": "10.6.251.27",
            "server_downlink_port": 6011,
            "server_downlink_bandwidth": "250m",
            "server_downlink_duration": 60000,
            "server_downlink_packet_len": 1350,
            "server_uplink_listen_port": 7011,
        }
    }

    downlink = step_from_template("traffic_server_downlink_start", settings)
    uplink_receive = step_from_template("traffic_server_uplink_receive_start", settings)

    assert downlink.params["command"] == (
        "iperf -u -c 10.6.251.27 -i 1 -t 60000 -b 250m -l 1350 -p 6011 -P 1"
    )
    assert uplink_receive.params["command"] == "iperf -u -s -i 1 -p 7011"


def test_phone_iperf_steps_include_generated_arguments():
    settings = {
        "traffic": {
            "phone_uplink_target": "10.88.149.164",
            "phone_uplink_port": 7011,
            "phone_uplink_bandwidth": "120m",
            "phone_uplink_duration": 6000,
            "phone_uplink_packet_len": 1350,
            "phone_downlink_listen_port": 6011,
        }
    }

    downlink_receive = step_from_template("phone_downlink_receive_start", settings)
    uplink = step_from_template("phone_uplink_iperf_start", settings)

    assert downlink_receive.params["arguments"] == "-u -s -i 1 -p 6011"
    assert downlink_receive.params["command"] == "adb shell /data/local/tmp/iperf -u -s -i 1 -p 6011"
    assert uplink.params["arguments"] == (
        "-u -c 10.88.149.164 -i 1 -t 6000 -b 120m -l 1350 -p 7011 -P 1"
    )
    assert uplink.params["command"] == (
        "adb shell /data/local/tmp/iperf -u -c 10.88.149.164 -i 1 -t 6000 -b 120m -l 1350 -p 7011 -P 1"
    )


def test_builtin_case_templates_use_explicit_start_stop_order():
    templates = build_default_case_templates({"traffic_server_host": "10.88.149.164", "common": {"delay_seconds": 30}})
    downlink = next(item for item in templates if item.name == "下行灌包")
    uplink = next(item for item in templates if item.name == "上行灌包")

    assert [step.action for step in downlink.steps] == [
        "base_web_capture_start",
        "phone_downlink_receive_start",
        "traffic_server_downlink_start",
        "common_delay",
        "traffic_server_downlink_stop",
        "phone_downlink_receive_stop",
        "base_web_capture_stop",
    ]
    delay = downlink.steps[3]
    assert delay.params["delay_seconds"] == 30
    assert [step.action for step in uplink.steps] == [
        "base_web_capture_start",
        "traffic_server_uplink_receive_start",
        "phone_uplink_iperf_start",
        "common_delay",
        "phone_uplink_iperf_stop",
        "traffic_server_uplink_receive_stop",
        "base_web_capture_stop",
    ]


def test_builtin_rrc_template_contains_logging_repeat_and_cleanup_steps():
    templates = build_default_case_templates(
        {
            "base_web": {"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"},
            "ssh": {"host": "192.168.13.236", "port": 22, "username": "root", "password": "Root@236_", "log_output_dir": r"D:\test\mobile_automation_platform\ssh_log"},
            "traffic": {"server_ping_target": "10.6.250.2"},
        }
    )
    rrc = next(item for item in templates if item.name == "RRC 测试用例")

    assert "终端入网" in rrc.description
    assert [step.action for step in rrc.steps] == [
        "base_web_capture_start",
        "phone_airplane_cycle",
        "base_ssh_command_start",
        "base_ssh_command_start",
        "base_ssh_command_start",
        "traffic_server_down_ping_start",
        "base_ssh_command_repeat",
        "base_ssh_command_repeat",
        "traffic_server_down_ping_stop",
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "base_web_capture_stop",
    ]
    assert rrc.steps[1].params == {"detach_wait_seconds": 5, "attach_wait_seconds": 5}
    assert rrc.steps[2].params["session_key"] == "rrc_rlc_up"
    assert "dump-rlc-om-info" in rrc.steps[2].params["command"]
    assert rrc.steps[4].params["session_key"] == "rrc_cpu"
    assert "top -b -n 1" in rrc.steps[4].params["command"]
    assert rrc.steps[5].params["ping_target"] == "10.6.250.2"
    assert rrc.steps[6].params["repeat_count"] == 8
    assert rrc.steps[6].params["interval_seconds"] == 5
    assert "odi -n duapp0 release-ue" in rrc.steps[6].params["command"]
    assert "force-rlc-escape-ctrl" in rrc.steps[7].params["command"]


def test_rrc_template_uses_documented_ssh_log_and_control_commands():
    rrc = next(item for item in build_default_case_templates({}) if item.name == "RRC 测试用例")

    assert "odi -n duapp0 dump-rlc-om-info" in rrc.steps[2].params["command"]
    assert "odi -n upapp net-stat" in rrc.steps[2].params["command"]
    assert "show-mac-throughput-count" in rrc.steps[3].params["command"]
    assert "top -b -n 1" in rrc.steps[4].params["command"]
    assert "display-ue-info" in rrc.steps[6].params["command"]
    assert "odi -n duapp0 release-ue" in rrc.steps[6].params["command"]
    assert "odi -n duapp0 force-rlc-escape-ctrl 1" in rrc.steps[7].params["command"]


def test_rrc_template_uses_current_runtime_connection_settings():
    templates = build_default_case_templates(
        {
            "base_web": {"host": "192.168.13.236", "port": 8400, "capture_fapi_interface": "FAPI1"},
            "ssh": {
                "host": "192.168.13.236",
                "port": 22,
                "username": "root",
                "password": "Root@236_",
                "log_output_dir": r"D:\test\mobile_automation_platform\ssh_log",
            },
            "traffic": {"server_ping_target": "10.6.250.2"},
        }
    )
    rrc = next(item for item in templates if item.name == "RRC 测试用例")

    assert rrc.steps[0].params["capture_fapi_interface"] == "FAPI1"
    assert rrc.steps[2].params["ssh_host"] == "192.168.13.236"
    assert rrc.steps[2].params["ssh_password"] == "Root@236_"
    assert rrc.steps[5].params["ping_target"] == "10.6.250.2"


def test_rrc_template_uses_runtime_configured_ssh_log_commands():
    templates = build_default_case_templates(
        {
            "ssh": {
                "rlc_up_log_command": "custom rlc-up",
                "rate_log_command": "custom rate",
                "cpu_log_command": "custom cpu",
                "rrc_release_command": "custom release",
                "rrc_release_count": 7,
                "rrc_release_interval_seconds": 11,
                "force_rlc_escape_command": "custom force escape",
                "force_rlc_escape_count": 9,
                "force_rlc_escape_interval_seconds": 13,
            },
        }
    )
    rrc = next(item for item in templates if item.name == "RRC 测试用例")

    assert rrc.steps[2].params["command"] == "custom rlc-up"
    assert rrc.steps[3].params["command"] == "custom rate"
    assert rrc.steps[4].params["command"] == "custom cpu"
    assert rrc.steps[6].params["command"] == "custom release"
    assert rrc.steps[6].params["repeat_count"] == 7
    assert rrc.steps[6].params["interval_seconds"] == 11
    assert rrc.steps[7].params["command"] == "custom force escape"
    assert rrc.steps[7].params["repeat_count"] == 9
    assert rrc.steps[7].params["interval_seconds"] == 13


def test_remap_rrc_case_params_refreshes_configured_ssh_log_commands():
    old_settings = {
        "ssh": {
            "rlc_up_log_command": "old rlc-up",
            "rate_log_command": "old rate",
            "cpu_log_command": "old cpu",
            "rrc_release_command": "old release",
            "rrc_release_count": 3,
            "rrc_release_interval_seconds": 5,
            "force_rlc_escape_command": "old force",
            "force_rlc_escape_count": 3,
            "force_rlc_escape_interval_seconds": 5,
        }
    }
    new_settings = {
        "ssh": {
            "rlc_up_log_command": "new rlc-up",
            "rate_log_command": "new rate",
            "cpu_log_command": "new cpu",
            "rrc_release_command": "new release",
            "rrc_release_count": 6,
            "rrc_release_interval_seconds": 12,
            "force_rlc_escape_command": "new force",
            "force_rlc_escape_count": 8,
            "force_rlc_escape_interval_seconds": 14,
        }
    }
    case = next(item for item in build_default_case_templates(old_settings) if item.name == "RRC 测试用例")

    remap_case_params_from_settings(case, new_settings)

    assert case.steps[2].params["command"] == "new rlc-up"
    assert case.steps[3].params["command"] == "new rate"
    assert case.steps[4].params["command"] == "new cpu"
    assert case.steps[6].params["command"] == "new release"
    assert case.steps[6].params["repeat_count"] == 6
    assert case.steps[6].params["interval_seconds"] == 12
    assert case.steps[7].params["command"] == "new force"
    assert case.steps[7].params["repeat_count"] == 8
    assert case.steps[7].params["interval_seconds"] == 14


def test_remap_case_params_from_settings_updates_current_case_template_fields_only():
    old_settings = {
        "base_web": {"host": "192.168.13.236"},
        "traffic": {
            "server_host": "10.0.0.1",
            "server_username": "old-user",
            "server_downlink_bandwidth": "100M",
        },
    }
    new_settings = {
        "base_web": {"host": "192.168.13.250", "port": 8500},
        "traffic": {
            "server_host": "10.88.149.200",
            "server_username": "new-user",
            "server_password": "new-pass",
            "server_downlink_bandwidth": "250M",
            "server_downlink_duration": 120,
        },
    }
    case = SavedCase.new(
        "current",
        [
            step_from_template("traffic_server_downlink_start", old_settings),
            step_from_template("base_web_capture_start", old_settings),
        ],
    )
    case.steps[0].params["server_host"] = "manually-overridden"
    case.steps[0].params["custom_note"] = "keep me"
    case.steps[1].params["capture_fapi_interface"] = "FAPI3"

    changed = remap_case_params_from_settings(case, new_settings)

    assert changed == 9
    assert case.steps[0].params["server_host"] == "10.88.149.200"
    assert case.steps[0].params["server_user"] == "new-user"
    assert case.steps[0].params["server_password"] == "new-pass"
    assert case.steps[0].params["iperf_bandwidth"] == "250M"
    assert case.steps[0].params["iperf_duration"] == 120
    assert "-t 120 -b 250M" in case.steps[0].params["command"]
    assert case.steps[0].params["custom_note"] == "keep me"
    assert case.steps[1].params["web_host"] == "192.168.13.250"
    assert case.steps[1].params["web_port"] == 8500


def test_remap_case_params_preserves_per_step_delay_seconds():
    case = SavedCase.new(
        "delay case",
        [
            step_from_template("common_delay", {"common": {"delay_seconds": 5}}),
            step_from_template("common_delay", {"common": {"delay_seconds": 5}}),
        ],
    )
    case.steps[0].params["delay_seconds"] = "90"

    changed = remap_case_params_from_settings(case, {"common": {"delay_seconds": 5}})

    assert changed == 0
    assert case.steps[0].params["delay_seconds"] == "90"
    assert case.steps[1].params["delay_seconds"] == 5
