from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from desktop.case_operations import apply_device_overrides_to_payload, case_to_run_payload


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ReadinessItem:
    group: str
    label: str
    severity: Severity
    message: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class ReadinessGroup:
    name: str
    items: list[ReadinessItem] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    groups: list[ReadinessGroup]
    blocking_messages: list[str]

    @property
    def blocked(self) -> bool:
        return bool(self.blocking_messages)


def evaluate_case_readiness(
    case: Any,
    settings: dict[str, Any],
    selected_devices: list[str],
    preflight: dict[str, Any] | None = None,
    *,
    run_mode: str = "single",
) -> ReadinessResult:
    preflight = preflight or {}
    actions = _case_actions(case)
    items: list[ReadinessItem] = []

    _add_device_items(items, selected_devices, preflight)
    if _needs_web(actions):
        base_web = settings.get("base_web", {})
        _add_required(items, "基站 Web", "Web 地址", base_web.get("host"), "缺少基站 Web 地址")
        _add_required(items, "基站 Web", "Web 密码", base_web.get("password"), "缺少基站 Web 密码")
    if _needs_ssh(actions):
        ssh = settings.get("ssh", {})
        _add_required(items, "基站 SSH", "SSH 地址", ssh.get("host"), "缺少基站 SSH 地址")
        _add_required(items, "基站 SSH", "SSH 密码", ssh.get("password"), "缺少基站 SSH 密码")
    if _needs_traffic(actions):
        traffic = settings.get("traffic", {})
        _add_required(items, "灌包服务器", "服务器地址", traffic.get("server_host"), "缺少灌包服务器地址")
        _add_required(items, "灌包服务器", "服务器密码", traffic.get("server_password"), "缺少灌包服务器密码")
        payload = _payload_for_readiness(case, settings, selected_devices)
        if _needs_downlink(actions):
            _add_required(
                items,
                "灌包服务器",
                "下行目标 IP",
                _step_param(payload, "traffic_server_downlink_start", "server_downlink_target"),
                "下行灌包缺少服务器下行目标 IP",
            )
        if _needs_uplink(actions):
            _add_required(
                items,
                "灌包服务器",
                "上行目标 IP",
                _step_param(payload, "phone_uplink_iperf_start", "phone_uplink_target"),
                "上行灌包缺少手机上行目标 IP",
            )
    _add_device_mapping_items(items, settings.get("traffic", {}), selected_devices, required=run_mode == "dual")

    groups = _group_items(items)
    blocking = [item.message for item in items if item.required and item.severity == Severity.ERROR]
    return ReadinessResult(groups=groups, blocking_messages=blocking)


def _case_actions(case: Any) -> set[str]:
    steps = getattr(case, "steps", None)
    if steps is None and isinstance(case, dict):
        steps = case.get("steps") or []
    actions = set()
    for step in steps or []:
        if isinstance(step, dict):
            action = step.get("action") or step.get("kind")
        else:
            action = getattr(step, "action", "")
        if action:
            actions.add(str(action))
    return actions


def _payload_for_readiness(case: Any, settings: dict[str, Any], selected_devices: list[str]) -> dict:
    try:
        payload = case_to_run_payload(case, settings)
    except Exception:
        payload = case.to_dict() if hasattr(case, "to_dict") else dict(case or {})
    if selected_devices:
        payload = apply_device_overrides_to_payload(payload, settings, selected_devices[0])
    return payload


def _step_param(payload: dict, action: str, name: str) -> Any:
    for step in payload.get("steps") or []:
        if step.get("action") == action:
            return (step.get("params") or {}).get(name)
    return None


def _needs_web(actions: set[str]) -> bool:
    return any(action.startswith("base_web_") for action in actions)


def _needs_ssh(actions: set[str]) -> bool:
    return any(action.startswith("base_ssh_") for action in actions)


def _needs_traffic(actions: set[str]) -> bool:
    return _needs_downlink(actions) or _needs_uplink(actions) or any(
        action.startswith("traffic_server_") for action in actions
    )


def _needs_downlink(actions: set[str]) -> bool:
    return "traffic_server_downlink_start" in actions or "phone_downlink_receive_start" in actions


def _needs_uplink(actions: set[str]) -> bool:
    return "phone_uplink_iperf_start" in actions or "traffic_server_uplink_receive_start" in actions


def _add_device_items(items: list[ReadinessItem], selected_devices: list[str], preflight: dict[str, Any]) -> None:
    if selected_devices:
        device_text = ", ".join(selected_devices)
        items.append(ReadinessItem("手机端", "已选择设备", Severity.OK, f"已选择 {len(selected_devices)} 台设备: {device_text}"))
    else:
        items.append(ReadinessItem("手机端", "已选择设备", Severity.ERROR, "未选择手机设备"))

    if preflight.get("adb_ok", True):
        items.append(ReadinessItem("手机端", "ADB", Severity.OK, "ADB 可用"))
    else:
        items.append(ReadinessItem("手机端", "ADB", Severity.ERROR, "ADB 不可用"))


def _add_required(items: list[ReadinessItem], group: str, label: str, value: Any, missing_message: str) -> None:
    if str(value or "").strip():
        items.append(ReadinessItem(group, label, Severity.OK, "已配置"))
    else:
        items.append(ReadinessItem(group, label, Severity.ERROR, missing_message))


def _add_device_mapping_items(
    items: list[ReadinessItem],
    traffic: dict[str, Any],
    selected_devices: list[str],
    *,
    required: bool,
) -> None:
    if required:
        _add_dual_mapping_items(items, traffic, selected_devices)
        return

    overrides = traffic.get("device_overrides") or {}
    for device_id in selected_devices:
        values = overrides.get(device_id) or {}
        phone_ip = str(values.get("phone_ip") or values.get("server_downlink_target") or "").strip()
        if phone_ip:
            items.append(
                ReadinessItem(
                    "Device Mapping",
                    device_id,
                    Severity.OK,
                    _device_mapping_message(device_id, values),
                    required=False,
                )
            )


def _device_mapping_message(device_id: str, values: dict[str, Any]) -> str:
    phone_ip = values.get("phone_ip") or values.get("server_downlink_target") or ""
    downlink_port = values.get("downlink_port") or values.get("server_downlink_port") or values.get("phone_downlink_listen_port") or ""
    uplink_port = values.get("uplink_port") or values.get("server_uplink_listen_port") or values.get("phone_uplink_port") or ""
    parts = [f"{device_id} -> phone_ip {phone_ip}"]
    if downlink_port != "":
        parts.append(f"downlink_port {downlink_port}")
    if uplink_port != "":
        parts.append(f"uplink_port {uplink_port}")
    return ", ".join(parts)


def _add_dual_mapping_items(items: list[ReadinessItem], traffic: dict[str, Any], selected_devices: list[str]) -> None:
    overrides = traffic.get("device_overrides") or {}
    for device_id in selected_devices:
        values = overrides.get(device_id) or {}
        if str(values.get("phone_ip") or values.get("server_downlink_target") or "").strip():
            items.append(ReadinessItem("多设备映射", device_id, Severity.OK, f"{device_id} 已映射"))
        else:
            items.append(
                ReadinessItem("多设备映射", device_id, Severity.ERROR, f"双设备模式缺少 {device_id} 的手机 IP 映射")
            )


def _group_items(items: list[ReadinessItem]) -> list[ReadinessGroup]:
    order = ["手机端", "基站 Web", "基站 SSH", "灌包服务器", "多设备映射"]
    groups = [
        ReadinessGroup(name, [item for item in items if item.group == name])
        for name in order
        if any(item.group == name for item in items)
    ]
    for name in dict.fromkeys(item.group for item in items if item.group not in order):
        groups.append(ReadinessGroup(name, [item for item in items if item.group == name]))
    return groups
