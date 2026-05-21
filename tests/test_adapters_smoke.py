from pm_tests.core.adapters import AdapterRegistry, BaseWebAdapter, CommonAdapter, SnapshotAdapter, SshAdapter, TrafficAdapter, TrafficServerAdapter
from pm_tests.core.models import StepPlan


def test_traffic_adapter_ping_uses_device_ping(monkeypatch):
    calls = {}

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls["device_id"] = device_id

        def ping_test(self, host, count):
            calls["host"] = host
            calls["count"] = count
            return {"success": True, "success_count": count, "packet_loss": 0}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)

    result = TrafficAdapter("device-1").run_step(
        StepPlan(
            step_id="phone_ping",
            kind="phone_ping",
            adapter="traffic",
            parameters={"host": "10.0.0.1", "count": 5},
        )
    )

    assert result.success is True
    assert calls == {"device_id": "device-1", "host": "10.0.0.1", "count": 5}


def test_snapshot_adapter_returns_data(monkeypatch):
    class FakeMonitor:
        def __init__(self, device_id):
            pass

        def get_network_info(self):
            return {"success": True, "network": "5G"}

    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeMonitor)

    result = SnapshotAdapter("device-1").run_step(
        StepPlan(step_id="pre_snapshot", kind="snapshot", adapter="snapshot")
    )

    assert result.success is True
    assert result.data["network_info"]["network"] == "5G"


def test_base_web_adapter_accepts_explicit_capture_start_stop(monkeypatch):
    calls = []

    class FakeBaseWebClient:
        def start_capture(self, select_msg=None, transmit_ip=None):
            calls.append(("start", select_msg, transmit_ip))
            return type("Session", (), {"select_msg": select_msg, "transmit_ip": transmit_ip})()

        def stop_capture(self, session, download_dir=None):
            calls.append(("stop", session.select_msg, download_dir))
            return {"success": True, "local_path": "capture.pcap"}

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    start = adapter.run_step(
        StepPlan(
            "s1",
            "base_web_start_capture",
            "base_web",
            action="base_web_capture_start",
            parameters={"capture_signal_enabled": True, "capture_data_enabled": True, "capture_fapi_interface": "FAPI3"},
        )
    )
    stop = adapter.run_step(
        StepPlan("s2", "base_web_capture_stop", "base_web", action="base_web_capture_stop", parameters={"download_dir": "logs"})
    )

    assert start.success is True
    assert stop.success is True
    assert calls == [("start", "CP,UP,FAPI3", None), ("stop", "CP,UP,FAPI3", "logs")]


def test_base_web_capture_no_fapi_option_does_not_add_fapi(monkeypatch):
    calls = []

    class FakeBaseWebClient:
        def start_capture(self, select_msg=None, transmit_ip=None):
            calls.append(("start", select_msg))
            return type("Session", (), {"select_msg": select_msg, "transmit_ip": transmit_ip})()

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    result = adapter.run_step(
        StepPlan(
            "s1",
            "base_web_start_capture",
            "base_web",
            action="base_web_capture_start",
            parameters={"capture_signal_enabled": True, "capture_data_enabled": True, "capture_fapi_interface": "无"},
        )
    )

    assert result.success is True
    assert calls == [("start", "CP,UP")]


def test_base_web_adapter_builds_client_from_step_web_parameters(monkeypatch):
    created_settings = []

    class FakeBaseWebClient:
        def __init__(self, settings=None):
            created_settings.append(settings)

        def start_capture(self, select_msg=None, transmit_ip=None):
            return type("Session", (), {"select_msg": select_msg, "transmit_ip": transmit_ip})()

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    result = adapter.run_step(
        StepPlan(
            "s1",
            "base_web_start_capture",
            "base_web",
            action="base_web_capture_start",
            parameters={
                "web_host": "192.168.13.236",
                "web_port": 8400,
                "web_username": "web_user",
                "web_password": "web_password",
                "download_dir": "D:\\web_logs",
            },
        )
    )

    assert result.success is True
    assert created_settings[-1]["host"] == "192.168.13.236"
    assert created_settings[-1]["port"] == 8400
    assert created_settings[-1]["username"] == "web_user"
    assert created_settings[-1]["password"] == "web_password"
    assert created_settings[-1]["log_download_dir"] == "D:\\web_logs"


def test_ssh_adapter_accepts_explicit_log_start_stop(monkeypatch):
    calls = []

    class FakeBaseSshClient:
        def start_output_log(self, run_id, case_name):
            calls.append(("start", run_id, case_name))
            return type("Session", (), {"local_path": "ssh.log", "started_at": "2026-05-16T00:00:00"})()

        def stop_output_log(self, session):
            calls.append(("stop", session.local_path))
            return {"success": True, "local_path": session.local_path}

    monkeypatch.setattr("pm_tests.core.adapters.BaseSshClient", FakeBaseSshClient)
    adapter = SshAdapter()

    start = adapter.run_step(
        StepPlan("s1", "base_ssh_output_log", "ssh", action="base_ssh_log_start", parameters={"run_id": "run1", "case_name": "case1"})
    )
    stop = adapter.run_step(StepPlan("s2", "base_ssh_log_stop", "ssh", action="base_ssh_log_stop"))

    assert start.success is True
    assert stop.success is True
    assert calls == [("start", "run1", "case1"), ("stop", "ssh.log")]


def test_ssh_adapter_builds_client_from_step_ssh_parameters(monkeypatch):
    created_settings = []

    class FakeBaseSshClient:
        def __init__(self, settings=None):
            created_settings.append(settings)

        def start_output_log(self, run_id, case_name):
            return type("Session", (), {"local_path": "ssh.log", "started_at": "2026-05-16T00:00:00"})()

    monkeypatch.setattr("pm_tests.core.adapters.BaseSshClient", FakeBaseSshClient)
    adapter = SshAdapter()

    result = adapter.run_step(
        StepPlan(
            "s1",
            "base_ssh_output_log",
            "ssh",
            action="base_ssh_log_start",
            parameters={
                "ssh_host": "10.88.149.164",
                "ssh_port": 22,
                "ssh_username": "ssh_user",
                "ssh_password": "ssh_password",
                "ssh_log_output_dir": "D:\\ssh_logs",
                "ssh_log_command": "tail -f /tmp/base.log",
            },
        )
    )

    assert result.success is True
    assert created_settings[-1]["host"] == "10.88.149.164"
    assert created_settings[-1]["port"] == 22
    assert created_settings[-1]["username"] == "ssh_user"
    assert created_settings[-1]["password"] == "ssh_password"
    assert created_settings[-1]["log_output_dir"] == "D:\\ssh_logs"
    assert created_settings[-1]["log_command"] == "tail -f /tmp/base.log"


def test_ssh_adapter_runs_named_command_sessions_and_repeated_commands(monkeypatch):
    calls = []

    class FakeBaseSshClient:
        def __init__(self, settings=None):
            self.settings = settings

        def start_command(self, command, run_id, case_name, label=""):
            calls.append(("start_command", command, run_id, case_name, label))
            return type("Session", (), {"local_path": f"{label}.log", "started_at": "2026-05-19T00:00:00"})()

        def stop_output_log(self, session):
            calls.append(("stop", session.local_path))
            return {"success": True, "local_path": session.local_path}

        def run_command(self, command):
            calls.append(("run_command", command))
            return {"success": True, "stdout": "ok", "stderr": "", "exit_status": 0}

    monkeypatch.setattr("pm_tests.core.adapters.BaseSshClient", FakeBaseSshClient)
    monkeypatch.setattr("pm_tests.core.adapters.time.sleep", lambda _seconds: None)
    adapter = SshAdapter()

    start = adapter.run_step(
        StepPlan(
            "rlc",
            "base_ssh_command_start",
            "ssh",
            action="base_ssh_command_start",
            parameters={"command": "while true; do date; done", "session_key": "rlc_up", "run_id": "run1", "case_name": "rrc", "label": "rlc_up"},
        )
    )
    repeat = adapter.run_step(
        StepPlan(
            "release",
            "base_ssh_command_repeat",
            "ssh",
            action="base_ssh_command_repeat",
            parameters={"command": "release-ue", "repeat_count": 3, "interval_seconds": 5},
        )
    )
    stop = adapter.run_step(
        StepPlan(
            "stop",
            "base_ssh_command_stop",
            "ssh",
            action="base_ssh_command_stop",
            parameters={"session_key": "rlc_up"},
        )
    )

    assert start.success is True
    assert repeat.success is True
    assert repeat.data["attempt_count"] == 3
    assert stop.success is True
    assert calls == [
        ("start_command", "while true; do date; done", "run1", "rrc", "rlc_up"),
        ("run_command", "release-ue"),
        ("run_command", "release-ue"),
        ("run_command", "release-ue"),
        ("stop", "rlc_up.log"),
    ]


def test_registry_accepts_explicit_session_actions():
    registry = AdapterRegistry(device_id="device-1")
    steps = [
        StepPlan("s1", "base_web_start_capture", "base_web", action="base_web_capture_start"),
        StepPlan("s2", "base_web_capture_stop", "base_web", action="base_web_capture_stop"),
        StepPlan("s3", "server_downlink_iperf", "traffic_server", action="traffic_server_downlink_start"),
        StepPlan("s4", "stop_traffic_server", "traffic_server", action="traffic_server_downlink_stop"),
        StepPlan("s5", "phone_uplink_iperf", "traffic", action="phone_uplink_iperf_start"),
        StepPlan("s6", "stop_phone_traffic", "traffic", action="phone_uplink_iperf_stop"),
        StepPlan("s7", "base_ssh_command_start", "ssh", action="base_ssh_command_start"),
        StepPlan("s8", "base_ssh_command_stop", "ssh", action="base_ssh_command_stop"),
        StepPlan("s9", "base_ssh_command_repeat", "ssh", action="base_ssh_command_repeat"),
        StepPlan("s10", "phone_airplane_mode", "traffic", action="phone_airplane_mode_off"),
        StepPlan("s11", "phone_airplane_mode", "traffic", action="phone_airplane_mode_on"),
        StepPlan("s12", "phone_airplane_cycle", "traffic", action="phone_airplane_cycle"),
        StepPlan("s13", "common_delay", "common", action="common_delay"),
    ]

    assert all(registry.get(step.adapter).can_handle(step) for step in steps)


def test_action_specs_include_rrc_ssh_command_actions():
    from pm_tests.core.actions import resolve_action

    start = resolve_action("base_ssh_command_start")
    stop = resolve_action("base_ssh_command_stop")
    repeat = resolve_action("base_ssh_command_repeat")
    rlc = resolve_action("base_ssh_rlc_up_log_start")
    release = resolve_action("base_ssh_rrc_release_repeat")

    assert start.adapter == "ssh"
    assert start.kind == "base_ssh_command_start"
    assert stop.stop_action == "base_ssh_command_stop"
    assert repeat.adapter == "ssh"
    assert rlc.action == "base_ssh_command_start"
    assert rlc.kind == "base_ssh_command_start"
    assert release.action == "base_ssh_command_repeat"
    assert release.kind == "base_ssh_command_repeat"


def test_traffic_server_explicit_stop_only_stops_matching_session(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self, action):
            self.action = action
            self.command = f"{action} command"
            self.local_path = f"{action}.log"
            self.started_at = "2026-05-16T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append(("start", action, command, run_id, case_name))
            return FakeSession(action)

        def stop_command(self, session):
            calls.append(("stop", session.action))
            return {"success": True, "action": session.action, "local_path": session.local_path}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    adapter = TrafficServerAdapter()

    downlink_start = adapter.run_step(
        StepPlan(
            "s1",
            "server_downlink_iperf",
            "traffic_server",
            action="traffic_server_downlink_start",
            parameters={"command": "iperf down", "run_id": "run1", "case_name": "case1"},
        )
    )
    ping_start = adapter.run_step(
        StepPlan(
            "s2",
            "server_down_ping",
            "traffic_server",
            action="traffic_server_down_ping_start",
            parameters={"command": "ping", "run_id": "run1", "case_name": "case1"},
        )
    )
    downlink_stop = adapter.run_step(
        StepPlan("s3", "stop_traffic_server", "traffic_server", action="traffic_server_downlink_stop")
    )

    assert downlink_start.success is True
    assert ping_start.success is True
    assert downlink_stop.success is True
    assert calls == [
        ("start", "server_downlink_iperf", "iperf down", "run1", "case1"),
        ("start", "server_down_ping", "ping", "run1", "case1"),
        ("stop", "server_downlink_iperf"),
    ]


def test_repeated_explicit_starts_cleanup_previous_matching_sessions(monkeypatch):
    calls = []

    class FakeWebSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def __init__(self):
            self.count = 0

        def start_capture(self, select_msg=None, transmit_ip=None):
            self.count += 1
            calls.append(("web_start", self.count))
            return FakeWebSession(f"web-{self.count}")

        def stop_capture(self, session, download_dir=None):
            calls.append(("web_stop", session.select_msg))
            return {"success": True}

    class FakeSshSession:
        def __init__(self, name):
            self.local_path = name
            self.started_at = "2026-05-16T00:00:00"

    class FakeBaseSshClient:
        def __init__(self):
            self.count = 0

        def start_output_log(self, run_id, case_name):
            self.count += 1
            calls.append(("ssh_start", self.count))
            return FakeSshSession(f"ssh-{self.count}")

        def stop_output_log(self, session):
            calls.append(("ssh_stop", session.local_path))
            return {"success": True}

    class FakeTrafficTester:
        def __init__(self, device_id):
            pass

        def start_device_iperf_command(self, action, arguments):
            calls.append(("phone_start", action, arguments))
            return {"success": True}

        def stop_device_iperf_command(self, action):
            calls.append(("phone_stop", action))
            return {"success": True}

    class FakeServerSession:
        def __init__(self, command):
            self.action = command
            self.command = command
            self.local_path = f"{command}.log"
            self.started_at = "2026-05-16T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append(("server_start", command))
            return FakeServerSession(command)

        def stop_command(self, session):
            calls.append(("server_stop", session.command))
            return {"success": True}

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    monkeypatch.setattr("pm_tests.core.adapters.BaseSshClient", FakeBaseSshClient)
    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)

    web = BaseWebAdapter()
    web.run_step(StepPlan("w1", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    web.run_step(StepPlan("w2", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    ssh = SshAdapter()
    ssh.run_step(StepPlan("s1", "base_ssh_output_log", "ssh", action="base_ssh_log_start"))
    ssh.run_step(StepPlan("s2", "base_ssh_output_log", "ssh", action="base_ssh_log_start"))
    phone = TrafficAdapter("device-1")
    phone.run_step(StepPlan("p1", "phone_uplink_iperf", "traffic", action="phone_uplink_iperf_start", parameters={"arguments": "old"}))
    phone.run_step(StepPlan("p2", "phone_uplink_iperf", "traffic", action="phone_uplink_iperf_start", parameters={"arguments": "new"}))
    server = TrafficServerAdapter()
    server.run_step(StepPlan("t1", "server_downlink_iperf", "traffic_server", action="traffic_server_downlink_start", parameters={"command": "old"}))
    server.run_step(StepPlan("t2", "server_downlink_iperf", "traffic_server", action="traffic_server_downlink_start", parameters={"command": "new"}))

    assert ("web_stop", "web-1") in calls
    assert ("ssh_stop", "ssh-1") in calls
    assert ("phone_stop", "phone_uplink_iperf") in calls
    assert ("server_stop", "old") in calls


def test_repeated_explicit_start_failure_keeps_old_session_tracked(monkeypatch):
    class FakeSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def __init__(self):
            self.starts = 0

        def start_capture(self, select_msg=None, transmit_ip=None):
            self.starts += 1
            return FakeSession(f"session-{self.starts}")

        def stop_capture(self, session, download_dir=None):
            raise RuntimeError("stop failed")

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    first = adapter.run_step(StepPlan("s1", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    second = adapter.run_step(StepPlan("s2", "base_web_start_capture", "base_web", action="base_web_capture_start"))

    assert first.success is True
    assert second.success is False
    assert adapter.explicit_sessions["base_web_capture"].select_msg == "session-1"


def test_explicit_stop_failure_keeps_session_tracked(monkeypatch):
    class FakeSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def start_capture(self, select_msg=None, transmit_ip=None):
            return FakeSession("session-1")

        def stop_capture(self, session, download_dir=None):
            raise RuntimeError("stop failed")

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    start = adapter.run_step(StepPlan("s1", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    stop = adapter.run_step(StepPlan("s2", "base_web_capture_stop", "base_web", action="base_web_capture_stop"))

    assert start.success is True
    assert stop.success is False
    assert adapter.explicit_sessions["base_web_capture"].select_msg == "session-1"


def test_explicit_stop_false_result_keeps_session_tracked(monkeypatch):
    class FakeSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def start_capture(self, select_msg=None, transmit_ip=None):
            return FakeSession("session-1")

        def stop_capture(self, session, download_dir=None):
            return {"success": False, "message": "still running"}

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    start = adapter.run_step(StepPlan("s1", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    stop = adapter.run_step(StepPlan("s2", "base_web_capture_stop", "base_web", action="base_web_capture_stop"))

    assert start.success is True
    assert stop.success is False
    assert adapter.explicit_sessions["base_web_capture"].select_msg == "session-1"


def test_legacy_base_web_stop_false_result_keeps_session_tracked(monkeypatch):
    class FakeSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def start_capture(self, select_msg=None, transmit_ip=None):
            return FakeSession("session-1")

        def stop_capture(self, session, download_dir=None):
            return {"success": False, "message": "still running"}

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    start = adapter.run_step(StepPlan("s1", "base_web_start_capture", "base_web"))
    stop = adapter.run_step(StepPlan("s2", "base_web_capture_stop", "base_web"))

    assert start.success is True
    assert stop.success is False
    assert adapter.capture_session.select_msg == "session-1"


def test_legacy_ssh_stop_false_result_keeps_session_tracked(monkeypatch):
    class FakeSession:
        local_path = "ssh.log"
        started_at = "2026-05-16T00:00:00"

    class FakeBaseSshClient:
        def start_output_log(self, run_id, case_name):
            return FakeSession()

        def stop_output_log(self, session):
            return {"success": False, "message": "still running"}

    monkeypatch.setattr("pm_tests.core.adapters.BaseSshClient", FakeBaseSshClient)
    adapter = SshAdapter()

    start = adapter.run_step(StepPlan("s1", "base_ssh_log_start", "ssh"))
    stop = adapter.run_step(StepPlan("s2", "base_ssh_log_stop", "ssh"))

    assert start.success is True
    assert stop.success is False
    assert adapter.log_session.local_path == "ssh.log"


def test_repeated_explicit_start_false_stop_result_keeps_old_session_and_does_not_start_new(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self, name):
            self.select_msg = name
            self.transmit_ip = ""

    class FakeBaseWebClient:
        def __init__(self):
            self.starts = 0

        def start_capture(self, select_msg=None, transmit_ip=None):
            self.starts += 1
            calls.append(("start", self.starts))
            return FakeSession(f"session-{self.starts}")

        def stop_capture(self, session, download_dir=None):
            calls.append(("stop", session.select_msg))
            return {"success": False, "message": "still running"}

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    adapter = BaseWebAdapter()

    first = adapter.run_step(StepPlan("s1", "base_web_start_capture", "base_web", action="base_web_capture_start"))
    second = adapter.run_step(StepPlan("s2", "base_web_start_capture", "base_web", action="base_web_capture_start"))

    assert first.success is True
    assert second.success is False
    assert adapter.explicit_sessions["base_web_capture"].select_msg == "session-1"
    assert calls == [("start", 1), ("stop", "session-1")]


def test_traffic_server_explicit_stop_without_session_is_warning(monkeypatch):
    class FakeTrafficServerClient:
        pass

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    result = TrafficServerAdapter().run_step(
        StepPlan("s1", "stop_traffic_server", "traffic_server", action="traffic_server_downlink_stop")
    )

    assert result.success is True
    assert result.data["skipped"] is True
    assert "warning" in result.data


def test_traffic_server_down_ping_builds_command_from_target_when_missing(monkeypatch):
    calls = []

    class FakeSession:
        action = "server_down_ping"
        command = "ping 10.6.250.2 -n 5"
        local_path = "ping.log"
        started_at = "2026-05-19T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append((action, command, run_id, case_name))
            return FakeSession()

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    adapter = TrafficServerAdapter()

    result = adapter.run_step(
        StepPlan(
            "s1",
            "server_down_ping",
            "traffic_server",
            action="traffic_server_down_ping_start",
            parameters={"ping_target": "10.6.250.2", "ping_count": 5, "run_id": "run1", "case_name": "rrc"},
        )
    )

    assert result.success is True
    assert calls == [("server_down_ping", "ping 10.6.250.2 -n 5", "run1", "rrc")]


def test_traffic_server_down_ping_count_zero_runs_until_stop(monkeypatch):
    calls = []

    class FakeSession:
        action = "server_down_ping"
        command = "ping 10.6.250.2"
        local_path = "ping.log"
        started_at = "2026-05-20T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append(("start", action, command))
            return FakeSession()

        def stop_command(self, session):
            calls.append(("stop", session.action, session.command))
            return {"success": True, "action": session.action, "command": session.command, "local_path": session.local_path}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    adapter = TrafficServerAdapter()

    start = adapter.run_step(
        StepPlan(
            "s1",
            "server_down_ping",
            "traffic_server",
            action="traffic_server_down_ping_start",
            parameters={"ping_target": "10.6.250.2", "ping_count": 0},
        )
    )
    stop = adapter.run_step(
        StepPlan("s2", "stop_traffic_server", "traffic_server", action="traffic_server_down_ping_stop")
    )

    assert start.success is True
    assert stop.success is True
    assert calls == [
        ("start", "server_down_ping", "ping 10.6.250.2"),
        ("stop", "server_down_ping", "ping 10.6.250.2"),
    ]


def test_traffic_server_iperf_commands_are_generated_when_missing(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self, action, command):
            self.action = action
            self.command = command
            self.local_path = f"{action}.log"
            self.started_at = "2026-05-20T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append((action, command))
            return FakeSession(action, command)

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    adapter = TrafficServerAdapter()

    downlink = adapter.run_step(
        StepPlan(
            "s1",
            "server_downlink_iperf",
            "traffic_server",
            action="traffic_server_downlink_start",
            parameters={
                "server_downlink_target": "10.6.251.27",
                "server_downlink_duration": 60000,
                "server_downlink_bandwidth": "250m",
                "server_downlink_packet_len": 1350,
                "server_downlink_port": 6011,
            },
        )
    )
    uplink_receive = adapter.run_step(
        StepPlan(
            "s2",
            "server_uplink_receive",
            "traffic_server",
            action="traffic_server_uplink_receive_start",
            parameters={"server_uplink_listen_port": 7011},
        )
    )

    assert downlink.success is True
    assert uplink_receive.success is True
    assert calls == [
        ("server_downlink_iperf", "iperf -u -c 10.6.251.27 -i 1 -t 60000 -b 250m -l 1350 -p 6011 -P 1"),
        ("server_uplink_receive", "iperf -u -s -i 1 -p 7011"),
    ]


def test_phone_iperf_arguments_are_generated_when_missing(monkeypatch):
    calls = []

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls.append(("init", device_id))

        def start_device_iperf_command(self, action, arguments):
            calls.append(("start", action, arguments))
            return {"success": True, "action": action, "command": arguments}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    adapter = TrafficAdapter("device-1")

    downlink = adapter.run_step(
        StepPlan(
            "p1",
            "phone_downlink_receive",
            "traffic",
            action="phone_downlink_receive_start",
            parameters={"phone_downlink_listen_port": 6011},
        )
    )
    uplink = adapter.run_step(
        StepPlan(
            "p2",
            "phone_uplink_iperf",
            "traffic",
            action="phone_uplink_iperf_start",
            parameters={
                "phone_uplink_target": "10.88.149.164",
                "phone_uplink_duration": 6000,
                "phone_uplink_bandwidth": "120m",
                "phone_uplink_packet_len": 1350,
                "phone_uplink_port": 7011,
            },
        )
    )

    assert downlink.success is True
    assert uplink.success is True
    assert calls == [
        ("init", "device-1"),
        ("start", "phone_downlink_receive", "-u -s -i 1 -p 6011"),
        ("start", "phone_uplink_iperf", "-u -c 10.88.149.164 -i 1 -t 6000 -b 120m -l 1350 -p 7011 -P 1"),
    ]


def test_base_web_explicit_stop_without_session_is_warning(monkeypatch):
    class FakeBaseWebClient:
        pass

    monkeypatch.setattr("pm_tests.core.adapters.BaseWebClient", FakeBaseWebClient)
    result = BaseWebAdapter().run_step(
        StepPlan("s1", "base_web_capture_stop", "base_web", action="base_web_capture_stop")
    )

    assert result.success is True
    assert result.data["skipped"] is True
    assert "warning" in result.data


def test_phone_explicit_uplink_start_stop_uses_matching_session(monkeypatch):
    calls = []

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls.append(("init", device_id))

        def start_device_iperf_command(self, action, arguments):
            calls.append(("start", action, arguments))
            return {"success": True, "action": action}

        def stop_device_iperf_command(self, action):
            calls.append(("stop", action))
            return {"success": True, "action": action}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    adapter = TrafficAdapter("device-1")

    start = adapter.run_step(
        StepPlan(
            "s1",
            "phone_uplink_iperf",
            "traffic",
            action="phone_uplink_iperf_start",
            parameters={"arguments": "-c 10.0.0.1"},
        )
    )
    stop = adapter.run_step(
        StepPlan("s2", "stop_phone_traffic", "traffic", action="phone_uplink_iperf_stop")
    )

    assert start.success is True
    assert stop.success is True
    assert calls == [
        ("init", "device-1"),
        ("start", "phone_uplink_iperf", "-c 10.0.0.1"),
        ("stop", "phone_uplink_iperf"),
    ]


def test_phone_airplane_mode_actions_call_tester(monkeypatch):
    calls = []

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls.append(("init", device_id))

        def set_airplane_mode(self, enabled):
            calls.append(("airplane", enabled))
            return {"success": True, "enabled": enabled, "commands": [{"command": "adb shell settings"}]}

    class FakeNetworkMonitor:
        def __init__(self, device_id):
            calls.append(("monitor", device_id))

        def get_cell_info(self):
            return {"success": True, "cell_info": "mCellInfo=[CellIdentityLte:{ mPci=123 }]"}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeNetworkMonitor)
    adapter = TrafficAdapter("device-1")

    off = adapter.run_step(
        StepPlan("s1", "phone_airplane_mode", "traffic", action="phone_airplane_mode_off")
    )
    on = adapter.run_step(
        StepPlan("s2", "phone_airplane_mode", "traffic", action="phone_airplane_mode_on")
    )

    assert off.success is True
    assert on.success is True
    assert off.data["enabled"] is False
    assert on.data["enabled"] is True
    assert calls == [("init", "device-1"), ("airplane", False), ("monitor", "device-1"), ("airplane", True)]


def test_phone_airplane_mode_off_fails_when_attach_has_no_pci(monkeypatch):
    class FakeTrafficTester:
        def __init__(self, device_id):
            pass

        def set_airplane_mode(self, enabled):
            return {"success": True, "enabled": enabled, "commands": [{"command": "adb shell settings"}]}

    class FakeNetworkMonitor:
        def __init__(self, device_id):
            pass

        def get_cell_info(self):
            return {"success": True, "cell_info": "mServiceState=IN_SERVICE\nmCellInfo=[]"}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeNetworkMonitor)

    result = TrafficAdapter("device-1").run_step(
        StepPlan("s1", "phone_airplane_mode", "traffic", action="phone_airplane_mode_off")
    )

    assert result.success is False
    assert result.error.code == "TRAFFIC_ATTACH_PCI_MISSING"
    assert "PCI" in result.message


def test_phone_airplane_cycle_toggles_offline_waits_then_online(monkeypatch):
    calls = []

    class FakeTrafficTester:
        def __init__(self, device_id):
            calls.append(("init", device_id))

        def set_airplane_mode(self, enabled):
            calls.append(("airplane", enabled))
            return {
                "success": True,
                "enabled": enabled,
                "command": f"airplane {enabled}",
                "commands": [{"command": f"airplane {enabled}", "stdout": "", "stderr": "", "exit_status": 0}],
            }

    class FakeNetworkMonitor:
        def __init__(self, device_id):
            calls.append(("monitor", device_id))

        def get_cell_info(self):
            return {"success": True, "cell_info": "mCellInfo=[CellIdentityNr:{ mPci = 321 }]"}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeNetworkMonitor)
    monkeypatch.setattr("pm_tests.core.adapters.time.sleep", lambda seconds: calls.append(("sleep", seconds)))

    result = TrafficAdapter("device-1").run_step(
        StepPlan(
            "s1",
            "phone_airplane_cycle",
            "traffic",
            action="phone_airplane_cycle",
            parameters={"detach_wait_seconds": 2, "attach_wait_seconds": 3},
        )
    )

    assert result.success is True
    assert result.data["operation"] == "phone_airplane_cycle"
    assert [item["phase"] for item in result.data["results"]] == ["detach", "attach", "attach_validation"]
    assert calls == [
        ("init", "device-1"),
        ("airplane", True),
        ("sleep", 2),
        ("airplane", False),
        ("sleep", 3),
        ("monitor", "device-1"),
    ]


def test_phone_airplane_cycle_fails_when_attach_has_no_pci(monkeypatch):
    class FakeTrafficTester:
        def __init__(self, device_id):
            pass

        def set_airplane_mode(self, enabled):
            return {"success": True, "enabled": enabled, "commands": [{"command": f"airplane {enabled}"}]}

    class FakeNetworkMonitor:
        def __init__(self, device_id):
            pass

        def get_cell_info(self):
            return {"success": True, "cell_info": "mServiceState=IN_SERVICE\nmCellInfo=[]"}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    monkeypatch.setattr("pm_tests.core.adapters.NetworkMonitor", FakeNetworkMonitor)
    monkeypatch.setattr("pm_tests.core.adapters.time.sleep", lambda seconds: None)

    result = TrafficAdapter("device-1").run_step(
        StepPlan(
            "s1",
            "phone_airplane_cycle",
            "traffic",
            action="phone_airplane_cycle",
            parameters={"detach_wait_seconds": 1, "attach_wait_seconds": 1},
        )
    )

    assert result.success is False
    assert result.error.code == "TRAFFIC_ATTACH_PCI_MISSING"
    assert result.data["results"][-1]["phase"] == "attach_validation"


def test_common_delay_adapter_waits_configured_seconds(monkeypatch):
    calls = []
    monkeypatch.setattr("pm_tests.core.adapters.time.sleep", lambda seconds: calls.append(seconds))

    result = CommonAdapter().run_step(
        StepPlan("delay", "common_delay", "common", action="common_delay", parameters={"delay_seconds": 4})
    )

    assert result.success is True
    assert calls == [4]
    assert result.data["command"] == "delay 4s"
    assert result.data["stdout"] == "delay completed after 4s"


def test_phone_explicit_stop_without_session_is_warning(monkeypatch):
    class FakeTrafficTester:
        def __init__(self, device_id):
            pass

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    result = TrafficAdapter("device-1").run_step(
        StepPlan("s1", "stop_phone_traffic", "traffic", action="phone_uplink_iperf_stop")
    )

    assert result.success is True
    assert result.data["skipped"] is True
    assert "warning" in result.data


def test_legacy_stop_phone_traffic_stops_all_sessions(monkeypatch):
    calls = []

    class FakeTrafficTester:
        def __init__(self, device_id):
            pass

        def start_device_iperf_command(self, action, arguments):
            calls.append(("start", action))
            return {"success": True}

        def stop_device_iperf_command(self, action):
            calls.append(("stop", action))
            return {"success": True, "action": action}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficTester", FakeTrafficTester)
    adapter = TrafficAdapter("device-1")

    adapter.run_step(StepPlan("s1", "phone_uplink_iperf", "traffic"))
    adapter.run_step(StepPlan("s2", "phone_downlink_receive", "traffic"))
    result = adapter.run_step(StepPlan("s3", "stop_phone_traffic", "traffic"))

    assert result.success is True
    assert calls == [
        ("start", "phone_uplink_iperf"),
        ("start", "phone_downlink_receive"),
        ("stop", "phone_downlink_receive"),
        ("stop", "phone_uplink_iperf"),
    ]


def test_legacy_stop_traffic_server_stops_all_sessions(monkeypatch):
    calls = []

    class FakeSession:
        def __init__(self, action):
            self.action = action
            self.command = action
            self.local_path = f"{action}.log"
            self.started_at = "2026-05-16T00:00:00"

    class FakeTrafficServerClient:
        def start_command(self, action, command, run_id, case_name):
            calls.append(("start", action))
            return FakeSession(action)

        def stop_command(self, session):
            calls.append(("stop", session.action))
            return {"success": True, "action": session.action}

    monkeypatch.setattr("pm_tests.core.adapters.TrafficServerClient", FakeTrafficServerClient)
    adapter = TrafficServerAdapter()

    adapter.run_step(StepPlan("s1", "server_downlink_iperf", "traffic_server"))
    adapter.run_step(StepPlan("s2", "server_down_ping", "traffic_server"))
    result = adapter.run_step(StepPlan("s3", "stop_traffic_server", "traffic_server"))

    assert result.success is True
    assert calls == [
        ("start", "server_downlink_iperf"),
        ("start", "server_down_ping"),
        ("stop", "server_down_ping"),
        ("stop", "server_downlink_iperf"),
    ]
