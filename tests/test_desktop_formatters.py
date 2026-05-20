from desktop.formatters import extract_step_rows, format_error, format_run_console, format_run_summary


def test_extract_step_rows_uses_case_records_and_step_records():
    run = {
        "run_id": "run-1",
        "status": "failed",
        "case_records": [
            {
                "name": "case",
                "status": "failed",
                "step_records": [
                    {
                        "step_id": "phone_ping",
                        "kind": "phone_ping",
                        "adapter": "traffic",
                        "status": "failed",
                        "message": "Ping failed",
                        "error": {"code": "PING_FAILED", "adapter": "traffic", "message": "timeout"},
                    }
                ],
            }
        ],
    }

    rows = extract_step_rows(run)

    assert rows == [
        {
            "case": "case",
            "step": "phone_ping",
            "adapter": "traffic",
            "status": "failed",
            "message": "Ping failed",
            "error": "PING_FAILED traffic: timeout",
        }
    ]


def test_format_run_summary_uses_status_and_summary():
    text = format_run_summary({
        "run_id": "run-1",
        "device_id": "device-1",
        "status": "passed",
        "summary": {"passed": 2, "total": 3, "failed": 1},
    })

    assert "run-1" in text
    assert "device-1" in text
    assert "passed" in text
    assert "2/3" in text


def test_format_error_handles_missing_error():
    assert format_error(None) == ""
    assert format_error({"code": "X", "adapter": "adb", "message": "bad"}) == "X adb: bad"


def test_format_run_console_shows_progress_command_output_and_artifacts():
    run = {
        "case_records": [
            {
                "name": "test1",
                "step_records": [
                    {
                        "step_id": "s1",
                        "kind": "base_web_capture_start",
                        "adapter": "base_web",
                        "status": "passed",
                        "message": "started",
                        "data": {
                            "label": "基站 Web-开始抓包",
                            "command": "web capture CP FAPI1",
                            "return_preview": "started",
                        },
                        "artifacts": [{"kind": "pcap", "path": r"D:\test\autopm_system\log\a.pcap"}],
                    }
                ],
            }
        ],
    }

    text = format_run_console(run)

    assert "[1/1] test1 - 基站 Web-开始抓包" in text
    assert "命令: web capture CP FAPI1" in text
    assert "返回: started" in text
    assert r"产物: D:\test\autopm_system\log\a.pcap" in text


def test_format_run_console_uses_legacy_results_steps():
    run = {
        "run_id": "run-1",
        "results": [
            {
                "name": "legacy1",
                "status": "passed",
                "steps": ["phone_ping: passed ok"],
            }
        ],
    }

    text = format_run_console(run)

    assert "[1/1] legacy1 - step-1" in text
    assert "返回: phone_ping: passed ok" in text
    assert "No step records" not in text


def test_format_run_console_handles_list_commands_returns_and_artifacts():
    run = {
        "case_records": [
            {
                "name": "test1",
                "metadata": {"warnings": ["执行结束会尝试清理"]},
                "step_records": [
                    {
                        "step_id": "s1",
                        "kind": "traffic",
                        "status": "passed",
                        "data": {
                            "commands": ["cmd1", "cmd2"],
                            "stdout": ["out1", "out2"],
                            "warning": ["warn1", "warn2"],
                        },
                        "artifacts": ["a.log", {"path": "b.log"}],
                    }
                ],
            }
        ],
    }

    text = format_run_console(run)

    assert "命令: cmd1\ncmd2" in text
    assert "stdout: out1\nout2" in text
    assert "警告: warn1" in text
    assert "警告: warn2" in text
    assert "警告: 执行结束会尝试清理" in text
    assert "产物: a.log" in text
    assert "产物: b.log" in text


def test_format_run_console_shows_operation_stdout_stderr_and_local_path():
    run = {
        "case_records": [
            {
                "name": "RRC 测试用例",
                "step_records": [
                    {
                        "step_id": "ssh-1",
                        "kind": "base_ssh_command_once",
                        "adapter": "ssh",
                        "status": "passed",
                        "data": {
                            "operation": "base_ssh_command_once",
                            "command": "odi -n duapp0 display-ue-info",
                            "stdout": "Crnti 123",
                            "stderr": "warn",
                            "local_path": r"D:\test\mobile_automation_platform\ssh_log\rrc.log",
                        },
                    }
                ],
            }
        ]
    }

    text = format_run_console(run)

    assert "操作: base_ssh_command_once" in text
    assert "命令: odi -n duapp0 display-ue-info" in text
    assert "stdout: Crnti 123" in text
    assert "stderr: warn" in text
    assert r"产物: D:\test\mobile_automation_platform\ssh_log\rrc.log" in text


def test_format_run_console_shows_iperf_rate_line_and_preview():
    run = {
        "case_records": [
            {
                "name": "下行灌包",
                "step_records": [
                    {
                        "step_id": "phone",
                        "kind": "phone_downlink_receive",
                        "adapter": "traffic",
                        "status": "passed",
                        "data": {
                            "command": "adb shell /data/local/tmp/iperf -u -s -i 1 -p 6011",
                            "bandwidth_mbps": 249.0,
                            "rate_line": "[  1] 227.00-228.00 sec  29.6 MBytes   249 Mbits/sec",
                            "result_preview": "[  1] 227.00-228.00 sec  29.6 MBytes   249 Mbits/sec",
                        },
                    }
                ],
            }
        ]
    }

    text = format_run_console(run)

    assert "249.0 Mbps" in text
    assert "249 Mbits/sec" in text


def test_format_run_console_tails_existing_local_log_file(tmp_path):
    log_path = tmp_path / "rrc_cpu.log"
    log_path.write_text("\n".join(f"line-{index}" for index in range(1, 8)), encoding="utf-8")
    run = {
        "case_records": [
            {
                "name": "RRC 测试用例",
                "step_records": [
                    {
                        "step_id": "cpu",
                        "kind": "base_ssh_command_start",
                        "adapter": "ssh",
                        "status": "passed",
                        "data": {"local_path": str(log_path), "command": "top -b -n 1"},
                    }
                ],
            }
        ]
    }

    text = format_run_console(run)

    assert "实时日志:" in text
    assert "line-7" in text


def test_format_run_console_tails_log_artifact_when_data_path_missing(tmp_path):
    log_path = tmp_path / "rrc_rate.log"
    log_path.write_text("rate-line", encoding="utf-8")
    run = {
        "case_records": [
            {
                "name": "RRC 测试用例",
                "step_records": [
                    {
                        "step_id": "rate-stop",
                        "kind": "base_ssh_command_stop",
                        "adapter": "ssh",
                        "status": "passed",
                        "data": {},
                        "artifacts": [{"kind": "local_path", "path": str(log_path)}],
                    }
                ],
            }
        ]
    }

    text = format_run_console(run)

    assert "实时日志:" in text
    assert "rate-line" in text


def test_format_run_console_expands_repeated_command_inputs_and_outputs():
    run = {
        "case_records": [
            {
                "name": "RRC 娴嬭瘯鐢ㄤ緥",
                "step_records": [
                    {
                        "step_id": "release",
                        "kind": "base_ssh_command_repeat",
                        "adapter": "ssh",
                        "status": "passed",
                        "data": {
                            "operation": "base_ssh_command_repeat",
                            "command": "release-wrapper",
                            "results": [
                                {
                                    "command": "odi -n duapp0 release-ue 100",
                                    "stdout": "released 100",
                                    "stderr": "",
                                    "exit_status": 0,
                                },
                                {
                                    "command": "odi -n duapp0 release-ue 101",
                                    "stdout": "",
                                    "stderr": "not found",
                                    "exit_status": 1,
                                },
                            ],
                        },
                    }
                ],
            }
        ]
    }

    text = format_run_console(run)

    assert "鍛戒护缁撴灉[1]:" in text
    assert "input: odi -n duapp0 release-ue 100" in text
    assert "stdout: released 100" in text
    assert "exit_status: 0" in text
    assert "鍛戒护缁撴灉[2]:" in text
    assert "input: odi -n duapp0 release-ue 101" in text
    assert "stderr: not found" in text
    assert "exit_status: 1" in text
