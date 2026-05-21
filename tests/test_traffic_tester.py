from network.traffic_tester import TrafficTester


def test_set_airplane_mode_runs_settings_and_broadcast_commands(monkeypatch):
    calls = []

    class Result:
        def __init__(self, args, stdout="ok", returncode=0):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run_adb(args, *, device_id=None, check=False, timeout=None):
        calls.append((args, device_id, check, timeout))
        if args == ["shell", "settings", "get", "global", "airplane_mode_on"]:
            return Result(args, stdout="1" if len(calls) > 4 else "0")
        return Result(args)

    monkeypatch.setattr("network.traffic_tester.run_adb", fake_run_adb)

    off = TrafficTester("device-1").set_airplane_mode(False)
    on = TrafficTester("device-1").set_airplane_mode(True)

    assert off["success"] is True
    assert off["enabled"] is False
    assert on["success"] is True
    assert on["enabled"] is True
    assert calls == [
        (["shell", "sh -c 'cmd connectivity airplane-mode disable'"], "device-1", False, 20),
        (["shell", "sh -c 'settings put global airplane_mode_on 0'"], "device-1", False, 20),
        (["shell", "sh -c 'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false'"], "device-1", False, 20),
        (["shell", "settings", "get", "global", "airplane_mode_on"], "device-1", False, 10),
        (["shell", "sh -c 'cmd connectivity airplane-mode enable'"], "device-1", False, 20),
        (["shell", "sh -c 'settings put global airplane_mode_on 1'"], "device-1", False, 20),
        (["shell", "sh -c 'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true'"], "device-1", False, 20),
        (["shell", "settings", "get", "global", "airplane_mode_on"], "device-1", False, 10),
    ]
    assert off["commands"][0]["command"] == "adb -s device-1 shell cmd connectivity airplane-mode disable"
    assert on["commands"][0]["command"] == "adb -s device-1 shell cmd connectivity airplane-mode enable"
    assert off["observed_airplane_mode_on"] == "0"
    assert on["observed_airplane_mode_on"] == "1"


def test_set_airplane_mode_fails_when_selected_device_state_does_not_change(monkeypatch):
    class Result:
        returncode = 0
        stdout = "0"
        stderr = ""

    def fake_run_adb(args, *, device_id=None, check=False, timeout=None):
        assert device_id == "device-2"
        return Result()

    monkeypatch.setattr("network.traffic_tester.run_adb", fake_run_adb)

    result = TrafficTester("device-2").set_airplane_mode(True)

    assert result["success"] is False
    assert result["enabled"] is True
    assert "device-2" in result["error"]


def test_parse_iperf_output_promotes_latest_mbits_rate():
    text = "\n".join(
        [
            "[  1] 227.00-228.00 sec  29.6 MBytes   249 Mbits/sec   0.050 ms 135/24039 (0.56%)",
            "[  1] 228.00-229.00 sec  29.5 MBytes   248 Mbits/sec   0.049 ms 233/24039 (0.97%)",
        ]
    )

    parsed = TrafficTester("device-1")._parse_iperf_output(text)

    assert parsed["bandwidth_mbps"] == 248.0
    assert parsed["rate_line"] == "[  1] 228.00-229.00 sec  29.5 MBytes   248 Mbits/sec   0.049 ms 233/24039 (0.97%)"
    assert parsed["latest_interval"]["loss_percent"] == 0.97
