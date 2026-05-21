"""Canonical desktop case action and template definitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import config
from desktop.case_models import CaseStep, SavedCase


NO_FAPI = "无"


@dataclass(frozen=True, slots=True)
class ActionTemplate:
    action: str
    label: str
    group: str
    fields: list[dict[str, Any]] = field(default_factory=list)
    defaults: dict[str, Any] = field(default_factory=dict)


BASE_WEB_FIELDS = [
    {"name": "web_host", "label": "Web 地址", "type": "text"},
    {"name": "web_port", "label": "Web 端口", "type": "int"},
    {"name": "web_username", "label": "Web 用户名", "type": "text"},
    {"name": "web_password", "label": "Web 密码", "type": "password"},
    {"name": "download_dir", "label": "下载目录", "type": "path"},
    {"name": "capture_signal_enabled", "label": "抓取信令", "type": "bool"},
    {"name": "capture_data_enabled", "label": "抓取数据", "type": "bool"},
    {
        "name": "capture_fapi_interface",
        "label": "FAPI 接口",
        "type": "choice",
        "choices": [NO_FAPI, "FAPI1", "FAPI3"],
    },
]

BASE_SSH_FIELDS = [
    {"name": "ssh_host", "label": "SSH 地址", "type": "text"},
    {"name": "ssh_port", "label": "SSH 端口", "type": "int"},
    {"name": "ssh_username", "label": "SSH 用户名", "type": "text"},
    {"name": "ssh_password", "label": "SSH 密码", "type": "password"},
    {"name": "ssh_log_output_dir", "label": "SSH 日志目录", "type": "path"},
    {"name": "ssh_log_command", "label": "SSH 日志命令", "type": "text"},
]

BASE_SSH_COMMAND_FIELDS = [
    *BASE_SSH_FIELDS,
    {"name": "session_key", "label": "会话标识", "type": "text"},
    {"name": "label", "label": "日志标签", "type": "text"},
    {"name": "command", "label": "SSH 命令", "type": "text"},
    {"name": "repeat_count", "label": "重复次数", "type": "int"},
    {"name": "interval_seconds", "label": "间隔秒数", "type": "int"},
]

BASE_SSH_COMMAND_STOP_FIELDS = [
    *BASE_SSH_FIELDS,
    {"name": "session_key", "label": "会话标识", "type": "text"},
]

BASE_SSH_BUSINESS_LOG_FIELDS = [
    *BASE_SSH_FIELDS,
    {"name": "session_key", "label": "会话标识", "type": "text"},
    {"name": "label", "label": "日志标签", "type": "text"},
    {"name": "command", "label": "SSH 命令", "type": "text"},
]

BASE_SSH_BUSINESS_REPEAT_FIELDS = [
    *BASE_SSH_FIELDS,
    {"name": "command", "label": "SSH 命令", "type": "text"},
    {"name": "repeat_count", "label": "重复次数", "type": "int"},
    {"name": "interval_seconds", "label": "间隔秒数", "type": "int"},
]

SERVER_CONNECTION_FIELDS = [
    {"name": "server_host", "label": "服务器地址", "type": "text"},
    {"name": "server_user", "label": "用户名", "type": "text"},
    {"name": "server_password", "label": "密码", "type": "password"},
]

SERVER_IPERF_FIELDS = [
    *SERVER_CONNECTION_FIELDS,
    {"name": "iperf_port", "label": "端口", "type": "int"},
    {"name": "iperf_bandwidth", "label": "带宽", "type": "text"},
    {"name": "iperf_duration", "label": "时长", "type": "int"},
]

SERVER_PING_FIELDS = [
    *SERVER_CONNECTION_FIELDS,
    {"name": "ping_target", "label": "Ping 目标", "type": "text"},
    {"name": "ping_count", "label": "Ping 次数", "type": "int"},
]

SERVER_STOP_FIELDS = SERVER_CONNECTION_FIELDS
PHONE_AIRPLANE_FIELDS: list[dict[str, Any]] = []

PHONE_AIRPLANE_CYCLE_FIELDS = [
    {"name": "detach_wait_seconds", "label": "脱网等待秒数", "type": "int"},
    {"name": "attach_wait_seconds", "label": "入网等待秒数", "type": "int"},
]

COMMON_DELAY_FIELDS = [
    {"name": "delay_seconds", "label": "延时秒数", "type": "int"},
]

PHONE_IPERF_FIELDS = [
    {"name": "iperf_port", "label": "端口", "type": "int"},
    {"name": "iperf_bandwidth", "label": "带宽", "type": "text"},
    {"name": "iperf_duration", "label": "时长", "type": "int"},
]

PHONE_PING_FIELDS = [
    {"name": "server_host", "label": "目标地址", "type": "text"},
    {"name": "ping_count", "label": "Ping 次数", "type": "int"},
]


def _base_defaults(settings: dict[str, Any]) -> dict[str, Any]:
    base_web = dict(settings.get("base_web") or {})
    ssh = dict(settings.get("ssh") or {})
    traffic = dict(settings.get("traffic") or {})
    common = dict(settings.get("common") or {})
    server_host = traffic.get("server_host") or settings.get("traffic_server_host") or "10.88.149.164"
    return {
        "web_host": base_web.get("host") or settings.get("web_host") or settings.get("base_host") or "192.168.13.236",
        "web_port": int(base_web.get("port") or settings.get("web_port") or 8400),
        "web_username": base_web.get("username") or settings.get("web_username") or settings.get("base_username") or "root",
        "web_password": base_web.get("password") if "password" in base_web else settings.get("web_password", settings.get("base_password", "5GNR@root")),
        "ssh_host": ssh.get("host") or settings.get("ssh_host") or "10.88.149.164",
        "ssh_port": int(ssh.get("port") or settings.get("ssh_port") or 22),
        "ssh_username": ssh.get("username") or settings.get("ssh_username") or "root",
        "ssh_password": ssh.get("password") if "password" in ssh else settings.get("ssh_password", ""),
        "ssh_log_output_dir": ssh.get("log_output_dir") or settings.get("ssh_log_output_dir") or "D:\\test\\autopm_system\\log",
        "ssh_log_command": ssh.get("log_command") or settings.get("ssh_log_command") or "",
        "rlc_up_log_command": ssh.get("rlc_up_log_command") or ssh.get("log_command") or settings.get("rlc_up_log_command") or "",
        "rate_log_command": ssh.get("rate_log_command") or settings.get("rate_log_command") or "",
        "cpu_log_command": ssh.get("cpu_log_command") or settings.get("cpu_log_command") or "",
        "rrc_release_command": ssh.get("rrc_release_command") or settings.get("rrc_release_command") or "",
        "rrc_release_count": int(ssh.get("rrc_release_count") or settings.get("rrc_release_count") or 8),
        "rrc_release_interval_seconds": int(
            ssh.get("rrc_release_interval_seconds") or settings.get("rrc_release_interval_seconds") or 5
        ),
        "force_rlc_escape_command": ssh.get("force_rlc_escape_command") or settings.get("force_rlc_escape_command") or "",
        "force_rlc_escape_count": int(ssh.get("force_rlc_escape_count") or settings.get("force_rlc_escape_count") or 3),
        "force_rlc_escape_interval_seconds": int(
            ssh.get("force_rlc_escape_interval_seconds") or settings.get("force_rlc_escape_interval_seconds") or 5
        ),
        "server_host": server_host,
        "server_user": traffic.get("server_username") or settings.get("traffic_server_user") or "root",
        "server_password": traffic.get("server_password") if "server_password" in traffic else settings.get("traffic_server_password", "Root@164_"),
        "iperf_port": int(
            traffic.get("server_downlink_port")
            or traffic.get("server_uplink_listen_port")
            or settings.get("iperf_port")
            or 7011
        ),
        "iperf_bandwidth": traffic.get("server_downlink_bandwidth") or settings.get("iperf_bandwidth") or "100M",
        "iperf_duration": int(traffic.get("server_downlink_duration") or settings.get("iperf_duration") or 60),
        "server_downlink_target": traffic.get("server_downlink_target") or settings.get("server_downlink_target") or "",
        "server_downlink_port": int(traffic.get("server_downlink_port") or settings.get("server_downlink_port") or 6011),
        "server_downlink_bandwidth": traffic.get("server_downlink_bandwidth") or settings.get("server_downlink_bandwidth") or "250m",
        "server_downlink_duration": int(traffic.get("server_downlink_duration") or settings.get("server_downlink_duration") or 60000),
        "server_downlink_packet_len": int(traffic.get("server_downlink_packet_len") or settings.get("server_downlink_packet_len") or 1300),
        "server_uplink_listen_port": int(traffic.get("server_uplink_listen_port") or settings.get("server_uplink_listen_port") or 7011),
        "phone_uplink_target": traffic.get("phone_uplink_target") or settings.get("phone_uplink_target") or "",
        "phone_uplink_port": int(traffic.get("phone_uplink_port") or settings.get("phone_uplink_port") or 7011),
        "phone_uplink_bandwidth": traffic.get("phone_uplink_bandwidth") or settings.get("phone_uplink_bandwidth") or "120m",
        "phone_uplink_duration": int(traffic.get("phone_uplink_duration") or settings.get("phone_uplink_duration") or 6000),
        "phone_uplink_packet_len": int(traffic.get("phone_uplink_packet_len") or settings.get("phone_uplink_packet_len") or 1350),
        "phone_downlink_listen_port": int(traffic.get("phone_downlink_listen_port") or settings.get("phone_downlink_listen_port") or 6011),
        "ping_target": settings.get("ping_target") or traffic.get("server_ping_target") or settings.get("server_ping_target") or server_host,
        "ping_count": int(traffic.get("server_ping_count") if "server_ping_count" in traffic else settings.get("ping_count", 5)),
        "download_dir": settings.get("download_dir", "D:\\test\\autopm_system\\log"),
        "capture_signal_enabled": True,
        "capture_data_enabled": False,
        "capture_fapi_interface": base_web.get("capture_fapi_interface") or settings.get("capture_fapi_interface") or NO_FAPI,
        "detach_wait_seconds": int(settings.get("detach_wait_seconds") or 5),
        "attach_wait_seconds": int(settings.get("attach_wait_seconds") or 5),
        "delay_seconds": int(common.get("delay_seconds") or settings.get("delay_seconds") or 5),
    }


def _server_downlink_command(values: dict[str, Any]) -> str:
    return (
        f"iperf -u -c {values.get('server_downlink_target') or ''} "
        f"-i 1 -t {int(values.get('server_downlink_duration') or 60000)} "
        f"-b {values.get('server_downlink_bandwidth') or '250m'} "
        f"-l {int(values.get('server_downlink_packet_len') or 1300)} "
        f"-p {int(values.get('server_downlink_port') or 6011)} -P 1"
    )


def _server_uplink_receive_command(values: dict[str, Any]) -> str:
    return f"iperf -u -s -i 1 -p {int(values.get('server_uplink_listen_port') or 7011)}"


def _phone_downlink_receive_arguments(values: dict[str, Any]) -> str:
    return f"-u -s -i 1 -p {int(values.get('phone_downlink_listen_port') or 6011)}"


def _phone_uplink_arguments(values: dict[str, Any]) -> str:
    return (
        f"-u -c {values.get('phone_uplink_target') or ''} "
        f"-i 1 -t {int(values.get('phone_uplink_duration') or 6000)} "
        f"-b {values.get('phone_uplink_bandwidth') or '120m'} "
        f"-l {int(values.get('phone_uplink_packet_len') or 1350)} "
        f"-p {int(values.get('phone_uplink_port') or 7011)} -P 1"
    )


def _phone_command(arguments: str) -> str:
    return f"adb shell {config.DEVICE_IPERF_BINARY} {arguments}".strip()


def _rlc_up_log_command(defaults: dict[str, Any]) -> str:
    return (
        defaults.get("rlc_up_log_command")
        or "while true; do "
        "odi -n duapp0 dump-rlc-om-info; "
        "odi -n duapp0 display-mac-non-zero-om 1; "
        "odi -n duapp0 display-mac-non-zero-om 2; "
        "odi -n upapp net-stat; "
        "date; sleep 1; done"
    )


def _rate_log_command(defaults: dict[str, Any]) -> str:
    return (
        defaults.get("rate_log_command")
        or "numOfDuapp=`ps -ef | grep mac_phy_intf | grep duapp | wc -l`; "
        "while true; do clear; "
        "for ((i=0;i<$numOfDuapp;i++)); do odi -q -n duapp$i show-mac-throughput-count 5; done; "
        "date; sleep 2; done"
    )


def _cpu_log_command(defaults: dict[str, Any]) -> str:
    return defaults.get("cpu_log_command") or "while true; do top -b -n 1 | head -n 9; date; sleep 1; done"


def _rrc_release_command(defaults: dict[str, Any]) -> str:
    return (
        defaults.get("rrc_release_command")
        or "odi -n duapp0 display-ue-info | grep Crnti | awk '{print $3}' | "
        "xargs -r -I {} sh -c 'odi -n duapp0 release-ue {}'"
    )


def _force_rlc_escape_command(defaults: dict[str, Any]) -> str:
    return (
        defaults.get("force_rlc_escape_command")
        or "odi -n duapp0 display-ue-info | grep Super | awk '{print $3}' | "
        "xargs -r -I {} sh -c 'odi -n duapp0 force-rlc-escape-ctrl 1 {}'"
    )


def _ssh_connection_params(defaults: dict[str, Any]) -> dict[str, Any]:
    return {
        key: defaults[key]
        for key in ("ssh_host", "ssh_port", "ssh_username", "ssh_password", "ssh_log_output_dir")
        if key in defaults
    }


ACTIONS = [
    ActionTemplate("base_web_capture_start", "开始抓包", "基站 Web", BASE_WEB_FIELDS),
    ActionTemplate("base_web_capture_stop", "停止抓包", "基站 Web", BASE_WEB_FIELDS),
    ActionTemplate("base_web_collect_log", "收集日志", "基站 Web", BASE_WEB_FIELDS),
    ActionTemplate("base_ssh_log_start", "开始日志", "基站 SSH", BASE_SSH_FIELDS),
    ActionTemplate("base_ssh_log_stop", "停止日志", "基站 SSH", BASE_SSH_FIELDS),
    ActionTemplate("base_ssh_rlc_up_log_start", "开始 RLC/UP 日志", "基站 SSH", BASE_SSH_BUSINESS_LOG_FIELDS),
    ActionTemplate("base_ssh_rlc_up_log_stop", "停止 RLC/UP 日志", "基站 SSH", BASE_SSH_COMMAND_STOP_FIELDS),
    ActionTemplate("base_ssh_rate_log_start", "开始速率日志", "基站 SSH", BASE_SSH_BUSINESS_LOG_FIELDS),
    ActionTemplate("base_ssh_rate_log_stop", "停止速率日志", "基站 SSH", BASE_SSH_COMMAND_STOP_FIELDS),
    ActionTemplate("base_ssh_cpu_log_start", "开始 CPU 日志", "基站 SSH", BASE_SSH_BUSINESS_LOG_FIELDS),
    ActionTemplate("base_ssh_cpu_log_stop", "停止 CPU 日志", "基站 SSH", BASE_SSH_COMMAND_STOP_FIELDS),
    ActionTemplate("base_ssh_rrc_release_repeat", "RRC release 命令", "基站 SSH", BASE_SSH_BUSINESS_REPEAT_FIELDS),
    ActionTemplate("base_ssh_force_rlc_escape_repeat", "force-rlc-escape-ctrl 命令", "基站 SSH", BASE_SSH_BUSINESS_REPEAT_FIELDS),
    ActionTemplate("base_ssh_command_start", "启动自定义命令", "基站 SSH", BASE_SSH_COMMAND_FIELDS),
    ActionTemplate("base_ssh_command_stop", "停止自定义命令", "基站 SSH", BASE_SSH_COMMAND_STOP_FIELDS),
    ActionTemplate("base_ssh_command_once", "执行命令", "基站 SSH", BASE_SSH_COMMAND_FIELDS),
    ActionTemplate(
        "base_ssh_command_repeat",
        "重复执行命令",
        "基站 SSH",
        BASE_SSH_COMMAND_FIELDS,
        {"repeat_count": 3, "interval_seconds": 5},
    ),
    ActionTemplate("traffic_server_downlink_start", "开始下行灌包", "灌包服务器", SERVER_IPERF_FIELDS),
    ActionTemplate("traffic_server_downlink_stop", "停止下行灌包", "灌包服务器", SERVER_STOP_FIELDS),
    ActionTemplate("traffic_server_down_ping_start", "开始下行 ping", "灌包服务器", SERVER_PING_FIELDS),
    ActionTemplate("traffic_server_down_ping_stop", "停止下行 ping", "灌包服务器", SERVER_STOP_FIELDS),
    ActionTemplate("traffic_server_uplink_receive_start", "开始上行接收", "灌包服务器", SERVER_IPERF_FIELDS),
    ActionTemplate("traffic_server_uplink_receive_stop", "停止上行接收", "灌包服务器", SERVER_STOP_FIELDS),
    ActionTemplate("phone_downlink_receive_start", "开始下行接收", "手机", PHONE_IPERF_FIELDS),
    ActionTemplate("phone_downlink_receive_stop", "停止下行接收", "手机", PHONE_IPERF_FIELDS),
    ActionTemplate("phone_uplink_iperf_start", "开始上行灌包", "手机", PHONE_IPERF_FIELDS),
    ActionTemplate("phone_uplink_iperf_stop", "停止上行灌包", "手机", PHONE_IPERF_FIELDS),
    ActionTemplate("phone_ping", "手机 ping", "手机", PHONE_PING_FIELDS),
    ActionTemplate("phone_airplane_mode_off", "关闭飞行模式入网", "手机", PHONE_AIRPLANE_FIELDS),
    ActionTemplate("phone_airplane_mode_on", "开启飞行模式脱网", "手机", PHONE_AIRPLANE_FIELDS),
    ActionTemplate("phone_airplane_cycle", "飞行操作", "手机", PHONE_AIRPLANE_CYCLE_FIELDS),
    ActionTemplate("common_delay", "延时", "通用", COMMON_DELAY_FIELDS),
]

ACTION_BY_ID = {item.action: item for item in ACTIONS}


def step_from_template(action: str, settings: dict[str, Any]) -> CaseStep:
    template = ACTION_BY_ID[action]
    runtime_defaults = _base_defaults(settings)
    params = {
        field["name"]: runtime_defaults[field["name"]]
        for field in template.fields
        if field["name"] in runtime_defaults
    }
    params.update(dict(template.defaults))
    if action == "traffic_server_downlink_start":
        params["command"] = _server_downlink_command(runtime_defaults)
    elif action == "traffic_server_uplink_receive_start":
        params["command"] = _server_uplink_receive_command(runtime_defaults)
    elif action == "phone_downlink_receive_start":
        params["arguments"] = _phone_downlink_receive_arguments(runtime_defaults)
        params["command"] = _phone_command(params["arguments"])
    elif action == "phone_uplink_iperf_start":
        params["arguments"] = _phone_uplink_arguments(runtime_defaults)
        params["command"] = _phone_command(params["arguments"])
    elif action in {"base_ssh_rlc_up_log_start", "base_ssh_rate_log_start", "base_ssh_cpu_log_start"}:
        params.update(_ssh_connection_params(runtime_defaults))
        if action == "base_ssh_rlc_up_log_start":
            params.update({"command": _rlc_up_log_command(runtime_defaults), "session_key": "rrc_rlc_up", "label": "rrc_rlc_up"})
        elif action == "base_ssh_rate_log_start":
            params.update({"command": _rate_log_command(runtime_defaults), "session_key": "rrc_rate", "label": "rrc_rate"})
        else:
            params.update({"command": _cpu_log_command(runtime_defaults), "session_key": "rrc_cpu", "label": "rrc_cpu"})
    elif action in {"base_ssh_rlc_up_log_stop", "base_ssh_rate_log_stop", "base_ssh_cpu_log_stop"}:
        params.update(_ssh_connection_params(runtime_defaults))
        session_keys = {
            "base_ssh_rlc_up_log_stop": "rrc_rlc_up",
            "base_ssh_rate_log_stop": "rrc_rate",
            "base_ssh_cpu_log_stop": "rrc_cpu",
        }
        params["session_key"] = session_keys[action]
    elif action == "base_ssh_rrc_release_repeat":
        params.update(_ssh_connection_params(runtime_defaults))
        params["command"] = _rrc_release_command(runtime_defaults)
        params["repeat_count"] = int(runtime_defaults.get("rrc_release_count") or 8)
        params["interval_seconds"] = int(runtime_defaults.get("rrc_release_interval_seconds") or 5)
    elif action == "base_ssh_force_rlc_escape_repeat":
        params.update(_ssh_connection_params(runtime_defaults))
        params["command"] = _force_rlc_escape_command(runtime_defaults)
        params["repeat_count"] = int(runtime_defaults.get("force_rlc_escape_count") or 3)
        params["interval_seconds"] = int(runtime_defaults.get("force_rlc_escape_interval_seconds") or 5)
    return CaseStep.new(template.action, f"{template.group}-{template.label}", params)


def remap_case_params_from_settings(case: SavedCase, settings: dict[str, Any]) -> int:
    """Refresh known step parameters in one saved case from current runtime settings."""
    changed = 0
    if case.name == "RRC 测试用例":
        refreshed_case = _rrc_case(settings)
        for step, refreshed in zip(case.steps, refreshed_case.steps):
            if step.action != refreshed.action:
                continue
            for name, value in refreshed.params.items():
                if step.params.get(name) != value:
                    step.params[name] = value
                    changed += 1
            if step.required != refreshed.required:
                step.required = refreshed.required
                changed += 1
        return changed

    for step in case.steps:
        if step.action not in ACTION_BY_ID:
            continue
        if step.action == "common_delay":
            continue
        refreshed = step_from_template(step.action, settings)
        for name, value in refreshed.params.items():
            if step.params.get(name) != value:
                step.params[name] = value
                changed += 1
    return changed


def _case(name: str, actions: list[str], settings: dict[str, Any]) -> SavedCase:
    return SavedCase.new(name, [step_from_template(action, settings) for action in actions])


def _rrc_case(settings: dict[str, Any]) -> SavedCase:
    defaults = _base_defaults(settings)
    rlc_up_log_command = (
        defaults.get("rlc_up_log_command")
        or "while true; do "
        "odi -n duapp0 dump-rlc-om-info; "
        "odi -n duapp0 display-mac-non-zero-om 1; "
        "odi -n duapp0 display-mac-non-zero-om 2; "
        "odi -n upapp net-stat; "
        "date; sleep 1; done"
    )
    rate_log_command = (
        defaults.get("rate_log_command")
        or "numOfDuapp=`ps -ef | grep mac_phy_intf | grep duapp | wc -l`; "
        "while true; do clear; "
        "for ((i=0;i<$numOfDuapp;i++)); do odi -q -n duapp$i show-mac-throughput-count 5; done; "
        "date; sleep 2; done"
    )
    cpu_log_command = defaults.get("cpu_log_command") or "while true; do top -b -n 1 | head -n 9; date; sleep 1; done"
    rrc_release_command = (
        defaults.get("rrc_release_command")
        or "odi -n duapp0 display-ue-info | grep Crnti | awk '{print $3}' | "
        "xargs -r -I {} sh -c 'odi -n duapp0 release-ue {}'"
    )
    force_rlc_escape_command = (
        defaults.get("force_rlc_escape_command")
        or "odi -n duapp0 display-ue-info | grep Super | awk '{print $3}' | "
        "xargs -r -I {} sh -c 'odi -n duapp0 force-rlc-escape-ctrl 1 {}'"
    )

    def ssh_params(command: str, session_key: str = "", label: str = "") -> dict[str, Any]:
        params = {
            key: defaults[key]
            for key in ("ssh_host", "ssh_port", "ssh_username", "ssh_password", "ssh_log_output_dir")
            if key in defaults
        }
        params["command"] = command
        if session_key:
            params["session_key"] = session_key
        if label:
            params["label"] = label
        return params

    steps = [
        step_from_template("base_web_capture_start", settings),
        CaseStep.new(
            "base_ssh_command_start",
            "基站 SSH-收取 RLC/UP 日志",
            ssh_params(
                rlc_up_log_command,
                "rrc_rlc_up",
                "rrc_rlc_up",
            ),
        ),
        CaseStep.new(
            "base_ssh_command_start",
            "基站 SSH-收取速率日志",
            ssh_params(
                rate_log_command,
                "rrc_rate",
                "rrc_rate",
            ),
        ),
        CaseStep.new(
            "base_ssh_command_start",
            "基站 SSH-收取 CPU 日志",
            ssh_params(cpu_log_command, "rrc_cpu", "rrc_cpu"),
        ),
        step_from_template("phone_airplane_mode_off", settings),
        step_from_template("traffic_server_down_ping_start", settings),
        CaseStep.new(
            "base_ssh_command_repeat",
            "基站 SSH-重复执行 RRC release",
            {
                **ssh_params(
                    rrc_release_command
                ),
                "repeat_count": int(defaults.get("rrc_release_count") or 8),
                "interval_seconds": int(defaults.get("rrc_release_interval_seconds") or 5),
            },
        ),
        CaseStep.new(
            "base_ssh_command_repeat",
            "基站 SSH-重复执行 force-rlc-escape-ctrl",
            {
                **ssh_params(
                    force_rlc_escape_command
                ),
                "repeat_count": int(defaults.get("force_rlc_escape_count") or 3),
                "interval_seconds": int(defaults.get("force_rlc_escape_interval_seconds") or 5),
            },
        ),
        step_from_template("traffic_server_down_ping_stop", settings),
        CaseStep.new("base_ssh_command_stop", "基站 SSH-停止 RLC/UP 日志", ssh_params("", "rrc_rlc_up")),
        CaseStep.new("base_ssh_command_stop", "基站 SSH-停止速率日志", ssh_params("", "rrc_rate")),
        CaseStep.new("base_ssh_command_stop", "基站 SSH-停止 CPU 日志", ssh_params("", "rrc_cpu")),
        step_from_template("phone_airplane_mode_on", settings),
        step_from_template("base_web_capture_stop", settings),
    ]
    steps[0].required = False
    steps[5].required = False
    steps[8].required = False
    steps[-1].required = False
    description = (
        "手工步骤：先确认终端入网，再执行自动步骤；需要飞行脱网时由人工操作。"
        "预期结果：抓包文件生成，RLC/UP 日志、速率日志、CPU 日志生成，"
        "RRC release / force-rlc-escape-ctrl 可在日志中定位，终端入网、脱网状态符合预期。"
    )
    return SavedCase.new("RRC 测试用例", steps, description=description)


def build_default_case_templates(settings: dict[str, Any]) -> list[SavedCase]:
    return [
        _case(
            "下行灌包",
            [
                "base_web_capture_start",
                "base_ssh_rate_log_start",
                "common_delay",
                "phone_airplane_mode_off",
                "phone_downlink_receive_start",
                "traffic_server_downlink_start",
                "common_delay",
                "traffic_server_downlink_stop",
                "phone_downlink_receive_stop",
                "phone_airplane_mode_on",
                "common_delay",
                "base_ssh_rate_log_stop",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _case(
            "上行灌包",
            [
                "base_web_capture_start",
                "base_ssh_rate_log_start",
                "common_delay",
                "phone_airplane_mode_off",
                "traffic_server_uplink_receive_start",
                "phone_uplink_iperf_start",
                "common_delay",
                "phone_uplink_iperf_stop",
                "traffic_server_uplink_receive_stop",
                "phone_airplane_mode_on",
                "common_delay",
                "base_ssh_rate_log_stop",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _case(
            "双向灌包",
            [
                "base_web_capture_start",
                "base_ssh_rate_log_start",
                "common_delay",
                "phone_airplane_mode_off",
                "phone_downlink_receive_start",
                "traffic_server_downlink_start",
                "traffic_server_uplink_receive_start",
                "phone_uplink_iperf_start",
                "common_delay",
                "traffic_server_downlink_stop",
                "phone_downlink_receive_stop",
                "phone_uplink_iperf_stop",
                "traffic_server_uplink_receive_stop",
                "phone_airplane_mode_on",
                "common_delay",
                "base_ssh_rate_log_stop",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _case(
            "入网",
            [
                "base_web_capture_start",
                "phone_airplane_mode_off",
                "phone_airplane_mode_on",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _case(
            "下行 ping",
            [
                "base_web_capture_start",
                "traffic_server_down_ping_start",
                "phone_ping",
                "traffic_server_down_ping_stop",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _case(
            "全流程",
            [
                "base_web_capture_start",
                "base_ssh_log_start",
                "phone_downlink_receive_start",
                "traffic_server_downlink_start",
                "common_delay",
                "traffic_server_downlink_stop",
                "phone_downlink_receive_stop",
                "traffic_server_uplink_receive_start",
                "phone_uplink_iperf_start",
                "common_delay",
                "phone_uplink_iperf_stop",
                "traffic_server_uplink_receive_stop",
                "base_ssh_log_stop",
                "base_web_collect_log",
                "base_web_capture_stop",
            ],
            settings,
        ),
        _rrc_case(settings),
    ]
