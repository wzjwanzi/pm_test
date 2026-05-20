"""Business-module mapping for the runtime settings form UI."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SettingsField:
    key: str
    label: str
    kind: str = "text"
    choices: tuple[str, ...] = ()


class SettingsValidationError(ValueError):
    """Raised when form values cannot be converted to runtime settings."""


MODULE_LABELS = {
    "base_web": "基站 Web",
    "ssh": "基站 SSH",
    "traffic_server": "灌包服务器",
    "phone": "手机端",
    "common": "通用",
}

MODULE_FIELDS: dict[str, tuple[SettingsField, ...]] = {
    "base_web": (
        SettingsField("host", "地址"),
        SettingsField("port", "端口", "int"),
        SettingsField("username", "用户名"),
        SettingsField("password", "密码"),
        SettingsField("log_download_dir", "日志下载目录"),
        SettingsField("capture_signal_enabled", "抓取信令", "bool"),
        SettingsField("capture_data_enabled", "抓取数据", "bool"),
        SettingsField("capture_fapi_interface", "FAPI 接口", "choice", ("无", "FAPI1", "FAPI3")),
    ),
    "ssh": (
        SettingsField("host", "地址"),
        SettingsField("port", "端口", "int"),
        SettingsField("username", "用户名"),
        SettingsField("password", "密码"),
        SettingsField("log_output_dir", "日志输出目录"),
        SettingsField("rlc_up_log_command", "RLC/UP 日志命令", "multiline"),
        SettingsField("rate_log_command", "速率日志命令", "multiline"),
        SettingsField("cpu_log_command", "CPU 日志命令", "multiline"),
        SettingsField("rrc_release_command", "RRC release 命令", "multiline"),
        SettingsField("rrc_release_count", "RRC release 次数", "int"),
        SettingsField("rrc_release_interval_seconds", "RRC release 间隔(s)", "int"),
        SettingsField("force_rlc_escape_command", "force-rlc-escape 命令", "multiline"),
        SettingsField("force_rlc_escape_count", "force-rlc-escape 次数", "int"),
        SettingsField("force_rlc_escape_interval_seconds", "force-rlc-escape 间隔(s)", "int"),
        SettingsField("connect_timeout", "连接超时", "int"),
    ),
    "traffic_server": (
        SettingsField("server_host", "服务器地址"),
        SettingsField("server_port", "SSH port", "int"),
        SettingsField("server_username", "用户名"),
        SettingsField("server_password", "密码"),
        SettingsField("server_connect_timeout", "连接超时", "int"),
        SettingsField("server_log_dir", "日志目录"),
        SettingsField("server_downlink_target", "下行目标"),
        SettingsField("server_downlink_port", "下行端口", "int"),
        SettingsField("server_downlink_bandwidth", "下行带宽"),
        SettingsField("server_downlink_duration", "下行时长", "int"),
        SettingsField("server_downlink_packet_len", "下行包长", "int"),
        SettingsField("server_uplink_listen_port", "上行监听端口", "int"),
        SettingsField("server_ping_target", "Ping 目标"),
        SettingsField("server_ping_count", "Ping 次数(0为持续)", "int"),
    ),
    "phone": (
        SettingsField("iperf.tool", "Iperf 工具", "choice", ("iperf", "iperf3")),
        SettingsField("iperf.host", "Iperf 目标"),
        SettingsField("iperf.port", "Iperf 端口", "int"),
        SettingsField("iperf.bandwidth", "Iperf 带宽"),
        SettingsField("iperf.duration", "Iperf 时长", "int"),
        SettingsField("iperf.interval", "Iperf 间隔", "int"),
        SettingsField("iperf.packet_len", "Iperf 包长", "int"),
        SettingsField("iperf.protocol", "Iperf 协议", "choice", ("udp", "tcp")),
        SettingsField("ping.host", "Ping 目标"),
        SettingsField("ping.count", "Ping 次数", "int"),
        SettingsField("traffic.phone_uplink_target", "手机上行目标"),
        SettingsField("traffic.phone_uplink_port", "手机上行端口", "int"),
        SettingsField("traffic.phone_uplink_bandwidth", "手机上行带宽"),
        SettingsField("traffic.phone_uplink_duration", "手机上行时长", "int"),
        SettingsField("traffic.phone_uplink_packet_len", "手机上行包长", "int"),
        SettingsField("traffic.phone_downlink_listen_port", "手机下载监听端口", "int"),
        SettingsField("traffic.phone_ping_target", "手机 Ping 目标"),
    ),
    "common": (
        SettingsField("delay_seconds", "延时秒数", "int"),
    ),
}


def extract_business_modules(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return form-shaped values grouped by the four business modules."""
    traffic = settings.get("traffic") or {}
    return {
        "base_web": dict(settings.get("base_web") or {}),
        "ssh": dict(settings.get("ssh") or {}),
        "traffic_server": {
            field.key: traffic.get(field.key)
            for field in MODULE_FIELDS["traffic_server"]
        },
        "phone": {
            field.key: _get_nested_value(settings, field.key)
            for field in MODULE_FIELDS["phone"]
        },
        "common": dict(settings.get("common") or {}),
    }


def merge_business_module(
    settings: dict[str, Any],
    module: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """Merge one business module into a copied runtime settings dictionary."""
    if module not in MODULE_FIELDS:
        raise KeyError(f"Unknown settings module: {module}")

    merged = copy.deepcopy(settings)
    parsed = _parse_values(module, values)
    if module in {"base_web", "ssh"}:
        merged.setdefault(module, {}).update(parsed)
    elif module == "traffic_server":
        merged.setdefault("traffic", {}).update(parsed)
    elif module == "phone":
        for key, value in parsed.items():
            group, name = key.split(".", 1)
            merged.setdefault(group, {})[name] = value
    elif module == "common":
        merged.setdefault("common", {}).update(parsed)
    return merged


def merge_all_business_modules(
    settings: dict[str, Any],
    modules: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Merge all known business modules in stable display order."""
    merged = copy.deepcopy(settings)
    for module in MODULE_FIELDS:
        merged = merge_business_module(merged, module, modules.get(module, {}))
    return merged


def _parse_values(module: str, values: dict[str, Any]) -> dict[str, Any]:
    fields = {field.key: field for field in MODULE_FIELDS[module]}
    parsed: dict[str, Any] = {}
    for key, value in values.items():
        if key not in fields:
            continue
        field = fields[key]
        if field.kind == "int":
            parsed[key] = _parse_int(field, value)
        elif field.kind == "bool":
            parsed[key] = _parse_bool(field, value)
        elif field.kind == "choice":
            parsed[key] = _parse_choice(field, value)
        else:
            parsed[key] = "" if value is None else str(value)
    return parsed


def _get_nested_value(settings: dict[str, Any], dotted_key: str) -> Any:
    group, name = dotted_key.split(".", 1)
    return (settings.get(group) or {}).get(name)


def _parse_int(field: SettingsField, value: Any) -> int:
    if isinstance(value, bool):
        raise SettingsValidationError(f"{field.label} ({field.key}) must be an integer")
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise SettingsValidationError(f"{field.label} ({field.key}) must be an integer") from exc


def _parse_choice(field: SettingsField, value: Any) -> str:
    parsed = "" if value is None else str(value)
    if parsed not in field.choices:
        choices = ", ".join(field.choices)
        raise SettingsValidationError(f"{field.label} ({field.key}) must be one of: {choices}")
    return parsed


def _parse_bool(field: SettingsField, value: Any) -> bool:
    if isinstance(value, str):
        parsed = value.strip().lower()
        if parsed in {"1", "true", "yes", "on"}:
            return True
        if parsed in {"0", "false", "no", "off", ""}:
            return False
        raise SettingsValidationError(f"{field.label} ({field.key}) must be a boolean")
    return bool(value)
