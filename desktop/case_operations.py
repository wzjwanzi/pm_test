"""Operation instantiation and runtime parameter resolution."""
from __future__ import annotations

import copy
from typing import Any

import config
from desktop.case_models import CaseStep, SavedCase
from desktop.case_templates import ACTION_BY_ID, step_from_template


GENERATED_PARAM_NAMES = {"command", "arguments"}
LEGACY_ALWAYS_LOCAL_BY_ACTION = {
    "common_delay": {"delay_seconds"},
    "phone_airplane_cycle": {"detach_wait_seconds", "attach_wait_seconds"},
}


def create_step_from_action(action: str, settings: dict[str, Any], values: dict[str, Any] | None = None) -> CaseStep:
    """Create one operation step with only explicit user changes marked as overrides."""
    step = step_from_template(action, settings) if action in ACTION_BY_ID else CaseStep.new(action, action, {})
    overrides = calculate_param_overrides(action, values or {}, settings)
    step.param_overrides = overrides
    step.params = resolve_params_for_action(action, settings, overrides)
    return step


def update_step_parameters(step: CaseStep, values: dict[str, Any], settings: dict[str, Any]) -> None:
    """Update one saved step without changing sibling cases or global defaults."""
    step.param_overrides = calculate_param_overrides(step.action, values, settings)
    step.params = resolve_params_for_action(step.action, settings, step.param_overrides)


def apply_operation_defaults(action: str, values: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    """Merge edited operation-library values into runtime settings."""
    updated = copy.deepcopy(settings or {})
    if action.startswith("base_web_"):
        base_web = dict(updated.get("base_web") or {})
        field_map = {
            "web_host": "host",
            "web_port": "port",
            "web_username": "username",
            "web_password": "password",
            "download_dir": "log_download_dir",
            "capture_signal_enabled": "capture_signal_enabled",
            "capture_data_enabled": "capture_data_enabled",
            "capture_fapi_interface": "capture_fapi_interface",
        }
        for source, target in field_map.items():
            if source in values:
                base_web[target] = values[source]
        if "download_dir" in values:
            base_web["capture_download_dir"] = values["download_dir"]
        updated["base_web"] = base_web
    elif action.startswith("traffic_server_"):
        traffic = dict(updated.get("traffic") or {})
        field_map = {
            "server_host": "server_host",
            "server_user": "server_username",
            "server_password": "server_password",
            "server_uplink_listen_port": "server_uplink_listen_port",
            "ping_target": "server_ping_target",
            "ping_count": "server_ping_count",
        }
        for source, target in field_map.items():
            if source in values:
                traffic[target] = values[source]
        if action == "traffic_server_downlink_start":
            if "iperf_port" in values:
                traffic["server_downlink_port"] = values["iperf_port"]
            if "iperf_bandwidth" in values:
                traffic["server_downlink_bandwidth"] = values["iperf_bandwidth"]
            if "iperf_duration" in values:
                traffic["server_downlink_duration"] = values["iperf_duration"]
        updated["traffic"] = traffic
    elif action == "phone_uplink_iperf_start":
        traffic = dict(updated.get("traffic") or {})
        field_map = {
            "iperf_port": "phone_uplink_port",
            "iperf_bandwidth": "phone_uplink_bandwidth",
            "iperf_duration": "phone_uplink_duration",
        }
        for source, target in field_map.items():
            if source in values:
                traffic[target] = values[source]
        updated["traffic"] = traffic
    return updated


def calculate_param_overrides(action: str, values: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    defaults = _default_params(action, settings)
    overrides: dict[str, Any] = {}
    for name, value in (values or {}).items():
        if name in GENERATED_PARAM_NAMES:
            continue
        if defaults.get(name) != value:
            overrides[name] = value
    return overrides


def resolve_step_params(step: CaseStep, settings: dict[str, Any]) -> dict[str, Any]:
    if step.action not in ACTION_BY_ID:
        return copy.deepcopy(dict(step.params or {}))

    if step.param_overrides:
        return resolve_params_for_action(step.action, settings, step.param_overrides)

    defaults = _default_params(step.action, settings)
    legacy_local = _legacy_local_params(step, defaults)
    return resolve_params_for_action(step.action, settings, legacy_local)


def resolve_params_for_action(action: str, settings: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    params = _default_params(action, settings)
    params.update(copy.deepcopy(dict(overrides or {})))
    refresh_generated_params(action, params)
    return params


def refresh_generated_params(action: str, params: dict[str, Any]) -> None:
    if action == "traffic_server_downlink_start":
        _sync_downlink_iperf_aliases(params)
        target = params.get("server_downlink_target") or ""
        duration = int(params.get("server_downlink_duration") or params.get("iperf_duration") or 60000)
        bandwidth = params.get("server_downlink_bandwidth") or params.get("iperf_bandwidth") or "250m"
        packet_len = int(params.get("server_downlink_packet_len") or 1300)
        port = int(params.get("server_downlink_port") or params.get("iperf_port") or 6011)
        params["command"] = f"iperf -u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
    elif action == "traffic_server_uplink_receive_start":
        port = int(params.get("server_uplink_listen_port") or params.get("iperf_port") or 7011)
        params["command"] = f"iperf -u -s -i 1 -p {port}"
    elif action == "phone_downlink_receive_start":
        port = int(params.get("phone_downlink_listen_port") or params.get("iperf_port") or 6011)
        params["arguments"] = f"-u -s -i 1 -p {port}"
        params["command"] = f"adb shell {config.DEVICE_IPERF_BINARY} {params['arguments']}"
    elif action == "phone_uplink_iperf_start":
        _sync_uplink_iperf_aliases(params)
        target = params.get("phone_uplink_target") or ""
        duration = int(params.get("phone_uplink_duration") or params.get("iperf_duration") or 6000)
        bandwidth = params.get("phone_uplink_bandwidth") or params.get("iperf_bandwidth") or "120m"
        packet_len = int(params.get("phone_uplink_packet_len") or 1350)
        port = int(params.get("phone_uplink_port") or params.get("iperf_port") or 7011)
        params["arguments"] = f"-u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
        params["command"] = f"adb shell {config.DEVICE_IPERF_BINARY} {params['arguments']}"


def case_to_run_payload(item: Any, settings: dict[str, Any]) -> dict:
    if isinstance(item, SavedCase):
        payload = item.to_dict()
    elif hasattr(item, "to_dict"):
        payload = item.to_dict()
    elif isinstance(item, dict):
        payload = copy.deepcopy(item)
    else:
        payload = dict(item)

    if "steps" not in payload:
        return payload

    resolved_steps = []
    for raw_step in payload.get("steps") or []:
        step = CaseStep.from_dict(raw_step)
        step_payload = step.to_dict()
        step_payload["params"] = resolve_step_params(step, settings)
        resolved_steps.append(step_payload)
    payload["steps"] = resolved_steps
    return payload


def apply_device_overrides_to_payload(payload: dict, settings: dict[str, Any], device_id: str) -> dict:
    updated = copy.deepcopy(payload)
    overrides = ((settings.get("traffic") or {}).get("device_overrides") or {})
    override = overrides.get(device_id) or {}
    if not override:
        return updated
    for step in updated.get("steps") or []:
        params = step.setdefault("params", {})
        action = str(step.get("action") or "")
        _apply_traffic_override_to_step(action, params, override)
    return updated


def _apply_traffic_override_to_step(action: str, params: dict, override: dict) -> None:
    if action == "traffic_server_downlink_start":
        _copy_override(params, override, "server_downlink_target")
        _copy_override(params, override, "server_downlink_port")
        _copy_override(params, override, "server_downlink_port", target_key="iperf_port")
        _copy_override(params, override, "server_downlink_bandwidth")
        _copy_override(params, override, "server_downlink_bandwidth", target_key="iperf_bandwidth")
        _copy_override(params, override, "server_downlink_duration")
        _copy_override(params, override, "server_downlink_duration", target_key="iperf_duration")
        _copy_override(params, override, "server_downlink_packet_len")
        refresh_generated_params(action, params)
    elif action == "phone_downlink_receive_start":
        _copy_override(params, override, "phone_downlink_listen_port")
        refresh_generated_params(action, params)
    elif action == "traffic_server_uplink_receive_start":
        _copy_override(params, override, "server_uplink_listen_port")
        refresh_generated_params(action, params)
    elif action == "phone_uplink_iperf_start":
        _copy_override(params, override, "phone_uplink_target")
        _copy_override(params, override, "phone_uplink_port")
        _copy_override(params, override, "phone_uplink_port", target_key="iperf_port")
        _copy_override(params, override, "phone_uplink_bandwidth")
        _copy_override(params, override, "phone_uplink_bandwidth", target_key="iperf_bandwidth")
        _copy_override(params, override, "phone_uplink_duration")
        _copy_override(params, override, "phone_uplink_duration", target_key="iperf_duration")
        _copy_override(params, override, "phone_uplink_packet_len")
        refresh_generated_params(action, params)
    elif action == "traffic_server_down_ping_start":
        ping_target = override.get("ping_target") or override.get("server_ping_target")
        if ping_target is not None:
            params["ping_target"] = ping_target
        _copy_override(params, override, "server_ping_count", target_key="ping_count")
    elif action == "phone_ping":
        phone_ping_target = override.get("phone_ping_target") or override.get("traffic_server_ip")
        if phone_ping_target is not None:
            params["server_host"] = phone_ping_target
        _copy_override(params, override, "server_ping_count", target_key="ping_count")


def _copy_override(params: dict, override: dict, key: str, *, target_key: str | None = None) -> None:
    if key in override:
        params[target_key or key] = override[key]


def _sync_downlink_iperf_aliases(params: dict[str, Any]) -> None:
    alias_map = {
        "iperf_port": "server_downlink_port",
        "iperf_bandwidth": "server_downlink_bandwidth",
        "iperf_duration": "server_downlink_duration",
    }
    for alias, canonical in alias_map.items():
        if alias in params:
            params[canonical] = params[alias]


def _sync_uplink_iperf_aliases(params: dict[str, Any]) -> None:
    alias_map = {
        "iperf_port": "phone_uplink_port",
        "iperf_bandwidth": "phone_uplink_bandwidth",
        "iperf_duration": "phone_uplink_duration",
    }
    for alias, canonical in alias_map.items():
        if alias in params:
            params[canonical] = params[alias]


def _default_params(action: str, settings: dict[str, Any]) -> dict[str, Any]:
    if action not in ACTION_BY_ID:
        return {}
    return copy.deepcopy(step_from_template(action, settings).params)


def _legacy_local_params(step: CaseStep, defaults: dict[str, Any]) -> dict[str, Any]:
    local: dict[str, Any] = {}
    always_local = LEGACY_ALWAYS_LOCAL_BY_ACTION.get(step.action, set())
    for name, value in dict(step.params or {}).items():
        if name not in defaults or name in always_local:
            local[name] = copy.deepcopy(value)
    return local
