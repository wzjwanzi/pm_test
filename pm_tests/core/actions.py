"""Canonical PM action metadata."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionSpec:
    action: str
    kind: str
    adapter: str
    session_key: str = ""
    start_action: str = ""
    stop_action: str = ""


_ACTION_SPECS = {
    "base_web_capture_start": ActionSpec(
        "base_web_capture_start",
        "base_web_start_capture",
        "base_web",
        session_key="base_web_capture",
        start_action="base_web_capture_start",
        stop_action="base_web_capture_stop",
    ),
    "base_web_capture_stop": ActionSpec(
        "base_web_capture_stop",
        "base_web_capture_stop",
        "base_web",
        session_key="base_web_capture",
        start_action="base_web_capture_start",
        stop_action="base_web_capture_stop",
    ),
    "base_web_collect_log": ActionSpec("base_web_collect_log", "base_web_collect_log", "base_web"),
    "base_ssh_log_start": ActionSpec(
        "base_ssh_log_start",
        "base_ssh_output_log",
        "ssh",
        session_key="base_ssh_log",
        start_action="base_ssh_log_start",
        stop_action="base_ssh_log_stop",
    ),
    "base_ssh_log_stop": ActionSpec(
        "base_ssh_log_stop",
        "base_ssh_log_stop",
        "ssh",
        session_key="base_ssh_log",
        start_action="base_ssh_log_start",
        stop_action="base_ssh_log_stop",
    ),
    "base_ssh_command_start": ActionSpec(
        "base_ssh_command_start",
        "base_ssh_command_start",
        "ssh",
        session_key="base_ssh_command",
        start_action="base_ssh_command_start",
        stop_action="base_ssh_command_stop",
    ),
    "base_ssh_command_stop": ActionSpec(
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "ssh",
        session_key="base_ssh_command",
        start_action="base_ssh_command_start",
        stop_action="base_ssh_command_stop",
    ),
    "base_ssh_command_once": ActionSpec("base_ssh_command_once", "base_ssh_command_once", "ssh"),
    "base_ssh_command_repeat": ActionSpec("base_ssh_command_repeat", "base_ssh_command_repeat", "ssh"),
    "base_ssh_rlc_up_log_start": ActionSpec(
        "base_ssh_command_start",
        "base_ssh_command_start",
        "ssh",
        session_key="rrc_rlc_up",
        start_action="base_ssh_rlc_up_log_start",
        stop_action="base_ssh_rlc_up_log_stop",
    ),
    "base_ssh_rlc_up_log_stop": ActionSpec(
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "ssh",
        session_key="rrc_rlc_up",
        start_action="base_ssh_rlc_up_log_start",
        stop_action="base_ssh_rlc_up_log_stop",
    ),
    "base_ssh_rate_log_start": ActionSpec(
        "base_ssh_command_start",
        "base_ssh_command_start",
        "ssh",
        session_key="rrc_rate",
        start_action="base_ssh_rate_log_start",
        stop_action="base_ssh_rate_log_stop",
    ),
    "base_ssh_rate_log_stop": ActionSpec(
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "ssh",
        session_key="rrc_rate",
        start_action="base_ssh_rate_log_start",
        stop_action="base_ssh_rate_log_stop",
    ),
    "base_ssh_cpu_log_start": ActionSpec(
        "base_ssh_command_start",
        "base_ssh_command_start",
        "ssh",
        session_key="rrc_cpu",
        start_action="base_ssh_cpu_log_start",
        stop_action="base_ssh_cpu_log_stop",
    ),
    "base_ssh_cpu_log_stop": ActionSpec(
        "base_ssh_command_stop",
        "base_ssh_command_stop",
        "ssh",
        session_key="rrc_cpu",
        start_action="base_ssh_cpu_log_start",
        stop_action="base_ssh_cpu_log_stop",
    ),
    "base_ssh_rrc_release_repeat": ActionSpec("base_ssh_command_repeat", "base_ssh_command_repeat", "ssh"),
    "base_ssh_force_rlc_escape_repeat": ActionSpec("base_ssh_command_repeat", "base_ssh_command_repeat", "ssh"),
    "traffic_server_downlink_start": ActionSpec(
        "traffic_server_downlink_start",
        "server_downlink_iperf",
        "traffic_server",
        session_key="traffic_server_downlink",
        start_action="traffic_server_downlink_start",
        stop_action="traffic_server_downlink_stop",
    ),
    "traffic_server_downlink_stop": ActionSpec(
        "traffic_server_downlink_stop",
        "stop_traffic_server",
        "traffic_server",
        session_key="traffic_server_downlink",
        start_action="traffic_server_downlink_start",
        stop_action="traffic_server_downlink_stop",
    ),
    "traffic_server_down_ping_start": ActionSpec(
        "traffic_server_down_ping_start",
        "server_down_ping",
        "traffic_server",
        session_key="traffic_server_down_ping",
        start_action="traffic_server_down_ping_start",
        stop_action="traffic_server_down_ping_stop",
    ),
    "traffic_server_down_ping_stop": ActionSpec(
        "traffic_server_down_ping_stop",
        "stop_traffic_server",
        "traffic_server",
        session_key="traffic_server_down_ping",
        start_action="traffic_server_down_ping_start",
        stop_action="traffic_server_down_ping_stop",
    ),
    "traffic_server_uplink_receive_start": ActionSpec(
        "traffic_server_uplink_receive_start",
        "server_uplink_receive",
        "traffic_server",
        session_key="traffic_server_uplink_receive",
        start_action="traffic_server_uplink_receive_start",
        stop_action="traffic_server_uplink_receive_stop",
    ),
    "traffic_server_uplink_receive_stop": ActionSpec(
        "traffic_server_uplink_receive_stop",
        "stop_traffic_server",
        "traffic_server",
        session_key="traffic_server_uplink_receive",
        start_action="traffic_server_uplink_receive_start",
        stop_action="traffic_server_uplink_receive_stop",
    ),
    "phone_downlink_receive_start": ActionSpec(
        "phone_downlink_receive_start",
        "phone_downlink_receive",
        "traffic",
        session_key="phone_downlink_receive",
        start_action="phone_downlink_receive_start",
        stop_action="phone_downlink_receive_stop",
    ),
    "phone_downlink_receive_stop": ActionSpec(
        "phone_downlink_receive_stop",
        "stop_phone_traffic",
        "traffic",
        session_key="phone_downlink_receive",
        start_action="phone_downlink_receive_start",
        stop_action="phone_downlink_receive_stop",
    ),
    "phone_uplink_iperf_start": ActionSpec(
        "phone_uplink_iperf_start",
        "phone_uplink_iperf",
        "traffic",
        session_key="phone_uplink_iperf",
        start_action="phone_uplink_iperf_start",
        stop_action="phone_uplink_iperf_stop",
    ),
    "phone_uplink_iperf_stop": ActionSpec(
        "phone_uplink_iperf_stop",
        "stop_phone_traffic",
        "traffic",
        session_key="phone_uplink_iperf",
        start_action="phone_uplink_iperf_start",
        stop_action="phone_uplink_iperf_stop",
    ),
    "phone_ping": ActionSpec("phone_ping", "phone_ping", "traffic"),
    "phone_airplane_mode_off": ActionSpec("phone_airplane_mode_off", "phone_airplane_mode", "traffic"),
    "phone_airplane_mode_on": ActionSpec("phone_airplane_mode_on", "phone_airplane_mode", "traffic"),
    "phone_airplane_cycle": ActionSpec("phone_airplane_cycle", "phone_airplane_cycle", "traffic"),
    "common_delay": ActionSpec("common_delay", "common_delay", "common"),
}


def resolve_action(action: str) -> ActionSpec:
    """Return metadata for a canonical explicit action."""

    try:
        return _ACTION_SPECS[str(action)]
    except KeyError as exc:
        raise ValueError(f"Unsupported action: {action}") from exc
