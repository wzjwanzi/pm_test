from pathlib import Path

from pm_tests.traffic_server import parse_iperf_log_file


def test_parse_iperf_log_file_promotes_latest_server_rate(tmp_path):
    log_path = tmp_path / "server_downlink.log"
    log_path.write_text(
        "\n".join(
            [
                "[  3] 215.0-216.0 sec  29.8 MBytes   250 Mbits/sec",
                "[  3] 216.0-217.0 sec  29.8 MBytes   250 Mbits/sec",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_iperf_log_file(Path(log_path))

    assert parsed["bandwidth_mbps"] == 250.0
    assert parsed["rate_line"] == "[  3] 216.0-217.0 sec  29.8 MBytes   250 Mbits/sec"
    assert "250 Mbits/sec" in parsed["result_preview"]
