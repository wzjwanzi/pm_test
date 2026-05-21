"""Persistent runtime settings for the desktop application."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import config


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    merged = copy.deepcopy(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _settings_file() -> Path:
    return Path(config.SETTINGS_FILE)


def load_runtime_settings() -> dict:
    """Load settings from disk and merge them with defaults."""
    path = _settings_file()
    defaults = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    if not path.exists():
        return defaults

    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    if not isinstance(loaded, dict):
        return defaults
    return normalize_runtime_settings(_deep_merge(defaults, loaded))


def save_runtime_settings(settings: dict) -> dict:
    """Persist settings to disk."""
    normalized = normalize_runtime_settings(settings)
    path = _settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized


def save_runtime_settings_group(group: str, group_settings: dict) -> dict:
    """Persist one top-level settings group without replacing sibling groups."""
    if group not in config.DEFAULT_RUNTIME_SETTINGS:
        raise KeyError(f"Unknown runtime settings group: {group}")
    current = load_runtime_settings()
    current[group] = group_settings
    return save_runtime_settings(current)


def reset_runtime_settings() -> dict:
    """Reset settings to defaults."""
    defaults = copy.deepcopy(config.DEFAULT_RUNTIME_SETTINGS)
    return save_runtime_settings(defaults)


def normalize_runtime_settings(settings: dict) -> dict:
    """Coerce persisted values to stable types."""
    merged = _deep_merge(config.DEFAULT_RUNTIME_SETTINGS, settings or {})

    base_web = merged["base_web"]
    base_web["host"] = str(base_web.get("host") or "").strip()
    base_web["port"] = int(base_web.get("port") or 8400)
    base_web["username"] = str(base_web.get("username") or "").strip()
    base_web["password"] = str(base_web.get("password") or "")
    base_web["log_download_dir"] = str(base_web.get("log_download_dir") or "").strip()
    base_web["capture_signal_enabled"] = _to_bool(base_web.get("capture_signal_enabled", True))
    base_web["capture_data_enabled"] = _to_bool(base_web.get("capture_data_enabled", False))
    if not base_web["capture_signal_enabled"] and not base_web["capture_data_enabled"]:
        base_web["capture_signal_enabled"] = True
    fapi = str(base_web.get("capture_fapi_interface") or "FAPI1").strip()
    if fapi in {"无", "鏃?"}:
        base_web["capture_fapi_interface"] = "无"
    else:
        base_web["capture_fapi_interface"] = fapi.upper()
    if base_web["capture_fapi_interface"] not in {"无", "FAPI1", "FAPI3"}:
        base_web["capture_fapi_interface"] = "FAPI1"
    base_web["capture_select_msg"] = _build_base_web_capture_select_msg(base_web)
    base_web["capture_transmit_ip"] = "" if base_web["capture_fapi_interface"] == "无" else base_web["capture_fapi_interface"]
    base_web["capture_download_dir"] = str(
        base_web.get("capture_download_dir") or base_web["log_download_dir"]
    ).strip()

    ssh = merged["ssh"]
    ssh["host"] = str(ssh.get("host") or "").strip()
    ssh["port"] = int(ssh.get("port") or 22)
    ssh["username"] = str(ssh.get("username") or "").strip()
    ssh["password"] = str(ssh.get("password") or "")
    ssh["log_output_dir"] = str(ssh.get("log_output_dir") or "").strip()
    ssh["log_command"] = str(ssh.get("log_command") or "").strip()
    ssh["rlc_up_log_command"] = str(ssh.get("rlc_up_log_command") or ssh["log_command"]).strip()
    ssh["rate_log_command"] = str(ssh.get("rate_log_command") or "").strip()
    ssh["cpu_log_command"] = str(ssh.get("cpu_log_command") or "").strip()
    ssh["rrc_release_command"] = str(ssh.get("rrc_release_command") or "").strip()
    ssh["rrc_release_count"] = max(int(ssh.get("rrc_release_count") or 8), 0)
    ssh["rrc_release_interval_seconds"] = max(int(ssh.get("rrc_release_interval_seconds") or 5), 0)
    ssh["force_rlc_escape_command"] = str(ssh.get("force_rlc_escape_command") or "").strip()
    ssh["force_rlc_escape_count"] = max(int(ssh.get("force_rlc_escape_count") or 3), 0)
    ssh["force_rlc_escape_interval_seconds"] = max(int(ssh.get("force_rlc_escape_interval_seconds") or 5), 0)
    ssh["connect_timeout"] = int(ssh.get("connect_timeout") or 20)

    ping = merged["ping"]
    ping["host"] = str(ping.get("host") or config.PING_APP_FIXED_HOST).strip()
    ping["count"] = max(int(ping.get("count") or config.PING_APP_FIXED_COUNT), 1)

    iperf = merged["iperf"]
    iperf["tool"] = str(iperf.get("tool") or "iperf3").strip().lower()
    if iperf["tool"] not in {"iperf3", "iperf"}:
        iperf["tool"] = "iperf3"
    iperf["host"] = str(iperf.get("host") or ping["host"]).strip()
    iperf["port"] = int(iperf.get("port") or 6087)
    iperf["bandwidth"] = str(iperf.get("bandwidth") or "120m").strip()
    iperf["duration"] = int(iperf.get("duration") or 60000)
    iperf["interval"] = int(iperf.get("interval") or 1)
    iperf["packet_len"] = int(iperf.get("packet_len") or 1350)
    iperf["protocol"] = str(iperf.get("protocol") or "udp").strip().lower()

    traffic = merged["traffic"]
    traffic["server_host"] = str(traffic.get("server_host") or "").strip()
    traffic["server_port"] = int(traffic.get("server_port") or 22)
    traffic["server_username"] = str(traffic.get("server_username") or "").strip()
    traffic["server_password"] = str(traffic.get("server_password") or "")
    traffic["server_connect_timeout"] = int(traffic.get("server_connect_timeout") or 20)
    traffic["server_log_dir"] = str(traffic.get("server_log_dir") or "").strip()
    traffic["server_downlink_target"] = str(traffic.get("server_downlink_target") or "").strip()
    traffic["server_downlink_port"] = int(traffic.get("server_downlink_port") or 6011)
    traffic["server_downlink_bandwidth"] = str(traffic.get("server_downlink_bandwidth") or "250m").strip()
    traffic["server_downlink_duration"] = int(traffic.get("server_downlink_duration") or 60000)
    traffic["server_downlink_packet_len"] = int(traffic.get("server_downlink_packet_len") or 1300)
    traffic["server_uplink_listen_port"] = int(traffic.get("server_uplink_listen_port") or 7011)
    traffic["server_ping_target"] = str(traffic.get("server_ping_target") or "").strip()
    traffic["server_ping_count"] = max(int(traffic.get("server_ping_count", 5)), 0)
    traffic["phone_uplink_target"] = str(traffic.get("phone_uplink_target") or "").strip()
    traffic["phone_uplink_port"] = int(traffic.get("phone_uplink_port") or 7011)
    traffic["phone_uplink_bandwidth"] = str(traffic.get("phone_uplink_bandwidth") or "120m").strip()
    traffic["phone_uplink_duration"] = int(traffic.get("phone_uplink_duration") or 6000)
    traffic["phone_uplink_packet_len"] = int(traffic.get("phone_uplink_packet_len") or 1350)
    traffic["phone_downlink_listen_port"] = int(traffic.get("phone_downlink_listen_port") or 6011)
    traffic["phone_ping_target"] = str(traffic.get("phone_ping_target") or "").strip()
    traffic["device_overrides"] = _normalize_traffic_device_overrides(traffic.get("device_overrides"), traffic)

    common = merged["common"]
    common["delay_seconds"] = max(int(common.get("delay_seconds") or 5), 0)

    return merged


def get_ping_settings() -> dict:
    return load_runtime_settings()["ping"]


def get_ssh_settings() -> dict:
    return load_runtime_settings()["ssh"]


def get_base_web_settings() -> dict:
    return load_runtime_settings()["base_web"]


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", "否"}
    return bool(value)


def _build_base_web_capture_select_msg(base_web: dict) -> str:
    parts = []
    if base_web.get("capture_signal_enabled"):
        parts.append("CP")
    if base_web.get("capture_data_enabled"):
        parts.append("UP")
    return ",".join(parts) or "CP"


def _normalize_traffic_device_overrides(raw_overrides, traffic: dict) -> dict:
    if isinstance(raw_overrides, str):
        try:
            raw_overrides = json.loads(raw_overrides)
        except json.JSONDecodeError:
            raw_overrides = {}
    if not isinstance(raw_overrides, dict):
        return {}

    normalized: dict[str, dict] = {}
    for raw_device_id, raw_values in raw_overrides.items():
        device_id = str(raw_device_id or "").strip()
        if not device_id or not isinstance(raw_values, dict):
            continue
        values = _normalize_one_traffic_device_override(raw_values, traffic)
        if values:
            normalized[device_id] = values
    return normalized


def _normalize_one_traffic_device_override(raw_values: dict, traffic: dict) -> dict:
    values = dict(raw_values)
    normalized: dict[str, object] = {}

    phone_ip = str(values.get("phone_ip") or "").strip()
    if phone_ip:
        normalized["phone_ip"] = phone_ip
        normalized["server_downlink_target"] = phone_ip
        normalized["server_ping_target"] = phone_ip
        normalized["ping_target"] = phone_ip
    for source, targets in (
        ("downlink_port", ("server_downlink_port", "phone_downlink_listen_port")),
        ("uplink_port", ("server_uplink_listen_port", "phone_uplink_port")),
    ):
        if source in values and str(values.get(source)).strip() != "":
            port = int(values[source])
            normalized[source] = port
            for target in targets:
                normalized[target] = port
    traffic_server_ip = str(values.get("traffic_server_ip") or "").strip()
    if traffic_server_ip:
        normalized["traffic_server_ip"] = traffic_server_ip
        normalized["phone_uplink_target"] = traffic_server_ip
        normalized["phone_ping_target"] = traffic_server_ip

    for key in (
        "server_downlink_target",
        "server_ping_target",
        "ping_target",
        "phone_uplink_target",
        "phone_ping_target",
    ):
        if key in values:
            normalized[key] = str(values.get(key) or "").strip()
    for key in (
        "server_downlink_port",
        "phone_downlink_listen_port",
        "server_uplink_listen_port",
        "phone_uplink_port",
        "server_ping_count",
        "phone_uplink_duration",
        "phone_uplink_packet_len",
    ):
        if key in values and str(values.get(key)).strip() != "":
            normalized[key] = int(values[key])
    for key in ("phone_uplink_bandwidth", "server_downlink_bandwidth", "server_downlink_duration", "server_downlink_packet_len"):
        if key in values:
            default = traffic.get(key) if isinstance(traffic, dict) else ""
            normalized[key] = str(values.get(key) or default or "").strip()
    if "phone_uplink_target" not in normalized and traffic.get("server_host"):
        normalized["phone_uplink_target"] = str(traffic.get("server_host") or "").strip()
    return normalized


def get_iperf_settings() -> dict:
    return load_runtime_settings()["iperf"]


def get_traffic_settings() -> dict:
    return load_runtime_settings()["traffic"]


def get_device_iperf_tool() -> str:
    return get_iperf_settings()["tool"]


def get_device_iperf_binary() -> str:
    if get_device_iperf_tool() == "iperf":
        return config.DEVICE_IPERF_BINARY
    return config.DEVICE_IPERF3_BINARY


def get_device_iperf_log() -> str:
    if get_device_iperf_tool() == "iperf":
        return config.DEVICE_IPERF_LOG
    return config.DEVICE_IPERF3_LOG


def build_device_iperf_arguments() -> str:
    settings = get_iperf_settings()
    protocol_flag = "-u" if settings["protocol"] == "udp" else ""
    parts = [
        protocol_flag,
        "-c",
        settings["host"],
        "-b",
        settings["bandwidth"],
        "-t",
        str(settings["duration"]),
        "-i",
        str(settings["interval"]),
        "-l",
        str(settings["packet_len"]),
        "-p",
        str(settings["port"]),
    ]
    return " ".join(part for part in parts if part)


def build_device_iperf_command() -> str:
    return f"{get_device_iperf_binary()} {build_device_iperf_arguments()}".strip()


def build_device_traffic_iperf_command(arguments: str) -> str:
    command = f"{get_device_iperf_binary()} {arguments}".strip()
    return f"adb shell {command}".strip()


def build_device_iperf3_arguments() -> str:
    return build_device_iperf_arguments()


def build_device_iperf3_command() -> str:
    return build_device_iperf_command()


def build_magic_iperf_arguments() -> str:
    return build_device_iperf_arguments()


def build_magic_iperf_command() -> str:
    return build_device_iperf_command()
