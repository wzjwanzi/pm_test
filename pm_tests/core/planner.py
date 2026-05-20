"""Compatibility planning from legacy PM case payloads."""
from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from pm_tests.core.actions import resolve_action
from pm_tests.core.models import CasePlan, RunPlan, StepPlan


FALSE_VALUES = {"0", "false", "no", "off", "否", "不"}
BASE_WEB_ACTIONS = {"base_web_collect_log", "base_web_start_capture"}
BASE_SSH_ACTIONS = {"base_ssh_output_log"}
TRAFFIC_ACTIONS = {
    "server_downlink_iperf",
    "server_down_ping",
    "server_uplink_receive",
    "phone_downlink_receive",
    "phone_uplink_iperf",
}


def parse_legacy_case_lines(case_lines: str, *, ping_defaults: dict) -> list[dict]:
    """Parse legacy comma-separated case lines into case dictionaries."""

    parsed_cases = []
    for index, raw_line in enumerate(str(case_lines or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [item.strip() for item in line.split(",")]
        parsed_cases.append(
            {
                "name": parts[0] if len(parts) >= 1 and parts[0] else f"用例{index}",
                "host": parts[1] if len(parts) >= 2 and parts[1] else ping_defaults["host"],
                "count": int(ping_defaults.get("count") or 5),
                "capture_enabled": _to_bool(parts[2]) if len(parts) >= 3 and parts[2] else True,
                "server_action": parts[3].lower() if len(parts) >= 4 and parts[3] else "none",
                "ping_enabled": _to_bool(parts[4]) if len(parts) >= 5 and parts[4] else True,
            }
        )
    return parsed_cases


def build_run_plan_from_legacy_cases(
    *,
    device_id: str,
    cases: list[dict],
    settings_snapshot: dict | None = None,
    run_id: str | None = None,
) -> RunPlan:
    """Build a typed RunPlan from legacy case dictionaries."""

    actual_run_id = run_id or f"pmrun-{uuid4().hex[:12]}"
    case_plans = [
        _case_plan_from_legacy(index, case, settings_snapshot or {}, actual_run_id)
        for index, case in enumerate(cases or [_default_case(settings_snapshot or {})], start=1)
    ]
    return RunPlan(
        run_id=actual_run_id,
        device_id=device_id,
        case_plans=case_plans,
        settings_snapshot=dict(settings_snapshot or {}),
    )


def build_run_plan(
    device_id: str,
    cases: list[dict],
    settings_snapshot: dict | None = None,
    run_id: str | None = None,
) -> RunPlan:
    """Build a RunPlan from explicit saved cases or legacy case payloads."""

    actual_run_id = run_id or f"pmrun-{uuid4().hex[:12]}"
    snapshot = dict(settings_snapshot or {})
    actual_cases = cases or [_default_case(snapshot)]
    case_plans = [
        _case_plan_from_explicit(index, case)
        if "steps" in case
        else _case_plan_from_legacy(index, case, snapshot, actual_run_id)
        for index, case in enumerate(actual_cases, start=1)
    ]
    return RunPlan(
        run_id=actual_run_id,
        device_id=device_id,
        case_plans=case_plans,
        settings_snapshot=snapshot,
    )


def _build_run_plan_from_explicit_cases(
    *,
    device_id: str,
    cases: list[dict],
    settings_snapshot: dict | None = None,
    run_id: str | None = None,
) -> RunPlan:
    actual_run_id = run_id or f"pmrun-{uuid4().hex[:12]}"
    case_plans = [
        _case_plan_from_explicit(index, case)
        for index, case in enumerate(cases or [], start=1)
    ]
    return RunPlan(
        run_id=actual_run_id,
        device_id=device_id,
        case_plans=case_plans,
        settings_snapshot=dict(settings_snapshot or {}),
    )


def _case_plan_from_explicit(index: int, case: dict) -> CasePlan:
    case_id = str(case.get("case_id") or f"case-{index:03d}")
    steps = []
    for step in case.get("steps") or []:
        if not bool(step.get("enabled", True)):
            continue
        action = str(step.get("action") or "")
        action_spec = resolve_action(action)
        steps.append(
            StepPlan(
                step_id=str(step.get("step_id") or action or f"step-{len(steps) + 1:03d}"),
                kind=action_spec.kind,
                adapter=action_spec.adapter,
                parameters=deepcopy(dict(step.get("params") or {})),
                required=bool(step.get("required", True)),
                action=action_spec.action,
                label=str(step.get("label") or ""),
            )
        )
    return CasePlan(
        case_id=case_id,
        name=str(case.get("name") or case_id),
        step_plans=steps,
        assertions={"required_steps_pass": True},
        metadata=dict(case),
    )


def _case_plan_from_legacy(index: int, case: dict, settings_snapshot: dict, run_id: str) -> CasePlan:
    case_id = str(case.get("case_id") or f"case-{index:03d}")
    host = str(case.get("host") or "8.8.8.8")
    count = int(case.get("count") or 5)
    actions = _split_actions(str(case.get("server_action") or "none"))
    steps = [
        StepPlan(step_id="pre_snapshot", kind="snapshot", adapter="snapshot", required=False),
    ]

    traffic = dict(settings_snapshot.get("traffic") or {})
    phone_traffic_started = False
    server_traffic_started = False

    for action in actions:
        if action in BASE_WEB_ACTIONS:
            steps.append(StepPlan(step_id=action, kind=action, adapter="base_web", required=False))
        elif action in BASE_SSH_ACTIONS:
            steps.append(StepPlan(step_id=action, kind=action, adapter="ssh", required=False))

    if "phone_downlink_receive" in actions:
        phone_traffic_started = True
        steps.append(
            StepPlan(
                step_id="phone_downlink_receive",
                kind="phone_downlink_receive",
                adapter="traffic",
                required=False,
                parameters={
                    "arguments": f"-u -s -i 1 -p {int(traffic.get('phone_downlink_listen_port') or 6011)}",
                },
            )
        )

    for action in ("server_uplink_receive", "server_downlink_iperf", "server_down_ping"):
        if action not in actions:
            continue
        server_traffic_started = True
        steps.append(
            StepPlan(
                step_id=action,
                kind=action,
                adapter="traffic_server",
                required=False,
                parameters={
                    "run_id": run_id,
                    "case_name": str(case.get("name") or case_id),
                    "command": _server_traffic_command(action, traffic),
                },
            )
        )

    if "phone_uplink_iperf" in actions:
        phone_traffic_started = True
        steps.append(
            StepPlan(
                step_id="phone_uplink_iperf",
                kind="phone_uplink_iperf",
                adapter="traffic",
                required=False,
                parameters={"arguments": _phone_uplink_arguments(traffic)},
            )
        )

    if bool(case.get("capture_enabled", False)):
        steps.append(
            StepPlan(
                step_id="device_capture",
                kind="device_capture",
                adapter="capture",
                parameters={"host": host},
                required=False,
            )
        )

    if bool(case.get("ping_enabled", True)):
        steps.append(
            StepPlan(
                step_id="phone_ping",
                kind="phone_ping",
                adapter="traffic",
                parameters={"host": host, "count": count},
            )
        )

    if phone_traffic_started:
        steps.append(
            StepPlan(
                step_id="stop_phone_traffic",
                kind="stop_phone_traffic",
                adapter="traffic",
                required=False,
            )
        )
    if server_traffic_started:
        steps.append(
            StepPlan(
                step_id="stop_traffic_server",
                kind="stop_traffic_server",
                adapter="traffic_server",
                required=False,
            )
        )

    steps.append(StepPlan(step_id="post_snapshot", kind="snapshot", adapter="snapshot", required=False))
    return CasePlan(
        case_id=case_id,
        name=str(case.get("name") or case_id),
        step_plans=steps,
        assertions={"required_steps_pass": True},
        metadata=dict(case),
    )


def _default_case(settings_snapshot: dict) -> dict:
    ping_settings = dict(settings_snapshot.get("ping") or {})
    return {
        "name": "默认Ping业务",
        "host": ping_settings.get("host") or "8.8.8.8",
        "count": int(ping_settings.get("count") or 5),
        "capture_enabled": False,
        "ping_enabled": True,
        "server_action": "none",
    }


def _split_actions(value: str) -> set[str]:
    return {
        item.strip().lower()
        for item in value.replace(";", ",").replace("|", ",").replace("+", ",").split(",")
        if item.strip() and item.strip().lower() != "none"
    }


def _server_traffic_command(action: str, traffic: dict) -> str:
    if action == "server_downlink_iperf":
        return (
            f"iperf -u -c {traffic.get('server_downlink_target') or ''} "
            f"-i 1 -t {int(traffic.get('server_downlink_duration') or 60000)} "
            f"-b {traffic.get('server_downlink_bandwidth') or '250m'} "
            f"-l {int(traffic.get('server_downlink_packet_len') or 1300)} "
            f"-p {int(traffic.get('server_downlink_port') or 6011)} -P 1"
        )
    if action == "server_uplink_receive":
        return f"iperf -u -s -i 1 -p {int(traffic.get('server_uplink_listen_port') or 7011)}"
    if action == "server_down_ping":
        return f"ping {traffic.get('server_ping_target') or ''}"
    return ""


def _phone_uplink_arguments(traffic: dict) -> str:
    return (
        f"-u -c {traffic.get('phone_uplink_target') or ''} "
        f"-i 1 -t {int(traffic.get('phone_uplink_duration') or 6000)} "
        f"-b {traffic.get('phone_uplink_bandwidth') or '120m'} "
        f"-l {int(traffic.get('phone_uplink_packet_len') or 1350)} "
        f"-p {int(traffic.get('phone_uplink_port') or 7011)} -P 1"
    )


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() not in FALSE_VALUES
