from pm_tests.core.planner import build_run_plan, build_run_plan_from_legacy_cases, parse_legacy_case_lines


def test_parse_legacy_case_lines_builds_cases():
    cases = parse_legacy_case_lines(
        "用例1,10.0.0.1,true,server_downlink_iperf,false",
        ping_defaults={"host": "8.8.8.8", "count": 5},
    )

    assert cases[0]["name"] == "用例1"
    assert cases[0]["host"] == "10.0.0.1"
    assert cases[0]["server_action"] == "server_downlink_iperf"
    assert cases[0]["ping_enabled"] is False


def test_build_run_plan_creates_step_sequence():
    plan = build_run_plan_from_legacy_cases(
        device_id="device-1",
        cases=[
            {
                "name": "case",
                "host": "10.0.0.1",
                "count": 5,
                "capture_enabled": True,
                "ping_enabled": True,
                "server_action": "base_ssh_output_log,phone_uplink_iperf",
            }
        ],
        settings_snapshot={"ping": {"host": "10.0.0.1", "count": 5}},
    )

    step_ids = [step.step_id for step in plan.case_plans[0].step_plans]
    assert "pre_snapshot" in step_ids
    assert "base_ssh_output_log" in step_ids
    assert "phone_uplink_iperf" in step_ids
    assert "device_capture" in step_ids
    assert "phone_ping" in step_ids
    assert "post_snapshot" in step_ids


def test_planner_preserves_explicit_case_step_order():
    plan = build_run_plan(
        "device-1",
        [
            {
                "case_id": "case_test1",
                "name": "test1",
                "steps": [
                    {
                        "step_id": "s1",
                        "action": "base_web_capture_start",
                        "label": "抓包开始",
                        "enabled": True,
                        "params": {"capture_fapi_interface": "FAPI3"},
                    },
                    {
                        "step_id": "s2",
                        "action": "phone_ping",
                        "label": "手机 ping",
                        "enabled": False,
                        "params": {"count": 3},
                    },
                    {
                        "step_id": "s3",
                        "action": "base_web_capture_stop",
                        "label": "抓包停止",
                        "enabled": True,
                        "params": {},
                    },
                ],
            }
        ],
    )

    case = plan.case_plans[0]
    assert case.case_id == "case_test1"
    assert [step.action for step in case.step_plans] == ["base_web_capture_start", "base_web_capture_stop"]
    assert [step.step_id for step in case.step_plans] == ["s1", "s3"]
    assert case.step_plans[0].parameters["capture_fapi_interface"] == "FAPI3"


def test_planner_deep_copies_explicit_step_params():
    params = {"capture": {"interfaces": ["FAPI1"]}}
    plan = build_run_plan(
        "device-1",
        [
            {
                "name": "test1",
                "steps": [
                    {
                        "step_id": "s1",
                        "action": "base_web_capture_start",
                        "label": "抓包开始",
                        "enabled": True,
                        "params": params,
                    }
                ],
            }
        ],
    )

    params["capture"]["interfaces"].append("FAPI3")

    assert plan.case_plans[0].step_plans[0].parameters == {"capture": {"interfaces": ["FAPI1"]}}


def test_planner_maps_explicit_actions_to_executable_kinds():
    plan = build_run_plan(
        "device-1",
        [
            {
                "name": "test1",
                "steps": [
                    {"step_id": "s1", "action": "phone_uplink_iperf_start", "label": "手机上行", "enabled": True},
                    {"step_id": "s2", "action": "phone_uplink_iperf_stop", "label": "停止手机上行", "enabled": True},
                    {"step_id": "s3", "action": "traffic_server_downlink_start", "label": "服务器下行", "enabled": True},
                    {"step_id": "s4", "action": "traffic_server_downlink_stop", "label": "停止服务器下行", "enabled": True},
                    {"step_id": "s5", "action": "base_web_capture_start", "label": "抓包开始", "enabled": True},
                ],
            }
        ],
    )

    steps = plan.case_plans[0].step_plans

    assert [step.action for step in steps] == [
        "phone_uplink_iperf_start",
        "phone_uplink_iperf_stop",
        "traffic_server_downlink_start",
        "traffic_server_downlink_stop",
        "base_web_capture_start",
    ]
    assert [step.kind for step in steps] == [
        "phone_uplink_iperf",
        "stop_phone_traffic",
        "server_downlink_iperf",
        "stop_traffic_server",
        "base_web_start_capture",
    ]


def test_planner_maps_business_ssh_actions_to_executable_ssh_kinds():
    plan = build_run_plan(
        "device-1",
        [
            {
                "name": "ssh business",
                "steps": [
                    {
                        "step_id": "rlc",
                        "action": "base_ssh_rlc_up_log_start",
                        "label": "开始 RLC/UP 日志",
                        "enabled": True,
                        "params": {"command": "custom rlc", "session_key": "rrc_rlc_up"},
                    },
                    {
                        "step_id": "release",
                        "action": "base_ssh_rrc_release_repeat",
                        "label": "RRC release 命令",
                        "enabled": True,
                        "params": {"command": "custom release", "repeat_count": 8},
                    },
                ],
            }
        ],
    )

    steps = plan.case_plans[0].step_plans

    assert [step.kind for step in steps] == ["base_ssh_command_start", "base_ssh_command_repeat"]
    assert [step.action for step in steps] == ["base_ssh_command_start", "base_ssh_command_repeat"]
    assert steps[0].parameters["session_key"] == "rrc_rlc_up"
    assert steps[1].parameters["command"] == "custom release"


def test_legacy_planner_uses_udp_receive_commands_for_iperf():
    plan = build_run_plan_from_legacy_cases(
        device_id="device-1",
        cases=[
            {
                "name": "traffic",
                "host": "10.0.0.1",
                "count": 0,
                "capture_enabled": False,
                "ping_enabled": False,
                "server_action": "phone_downlink_receive,server_uplink_receive",
            }
        ],
        settings_snapshot={
            "traffic": {
                "phone_downlink_listen_port": 6011,
                "server_uplink_listen_port": 7011,
            }
        },
    )

    params_by_kind = {step.kind: step.parameters for step in plan.case_plans[0].step_plans}

    assert params_by_kind["phone_downlink_receive"]["arguments"] == "-u -s -i 1 -p 6011"
    assert params_by_kind["server_uplink_receive"]["command"] == "iperf -u -s -i 1 -p 7011"


def test_legacy_planner_phone_uplink_uses_parallel_udp_command_arguments():
    plan = build_run_plan_from_legacy_cases(
        device_id="device-1",
        cases=[
            {
                "name": "traffic",
                "host": "10.0.0.1",
                "count": 0,
                "capture_enabled": False,
                "ping_enabled": False,
                "server_action": "phone_uplink_iperf",
            }
        ],
        settings_snapshot={
            "traffic": {
                "phone_uplink_target": "10.88.149.164",
                "phone_uplink_duration": 6000,
                "phone_uplink_bandwidth": "120m",
                "phone_uplink_packet_len": 1350,
                "phone_uplink_port": 7011,
            }
        },
    )

    params_by_kind = {step.kind: step.parameters for step in plan.case_plans[0].step_plans}

    assert params_by_kind["phone_uplink_iperf"]["arguments"] == (
        "-u -c 10.88.149.164 -i 1 -t 6000 -b 120m -l 1350 -p 7011 -P 1"
    )
