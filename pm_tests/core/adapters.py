"""Concrete adapter wrappers for existing PM integrations."""
from __future__ import annotations

import time
from typing import Any

from network.network_monitor import NetworkMonitor
from network.traffic_tester import TrafficTester
from pm_tests.base_ssh import BaseSshClient
from pm_tests.base_web import BaseWebClient
from pm_tests.capture import DeviceTcpdumpCaptureBackend, start_capture_with_fallback
from pm_tests.core.models import AdapterError, Artifact, StepPlan
from pm_tests.core.ports import AdapterResult
from pm_tests.traffic_server import TrafficServerClient


CLEANUP_WARNING = "执行结束会尝试清理"


class SnapshotAdapter:
    """Collect network snapshot information from a device."""

    def __init__(self, device_id: str):
        self.device_id = device_id

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) == "snapshot"

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            monitor = NetworkMonitor(self.device_id)
            network_info = monitor.get_network_info()
            data = {"network_info": network_info}
            if hasattr(monitor, "get_cell_info"):
                data["cell_info"] = monitor.get_cell_info()
            return _result_from_mapping(data, adapter="snapshot", message="Snapshot collected.")
        except Exception as exc:
            return _exception_result("snapshot", exc)


class CommonAdapter:
    """Run generic utility actions."""

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) == "common_delay"

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            seconds = max(0, int(dict(step.parameters).get("delay_seconds") or 0))
            time.sleep(seconds)
            data = {
                "success": True,
                "operation": "common_delay",
                "command": f"delay {seconds}s",
                "stdout": f"delay completed after {seconds}s",
                "delay_seconds": seconds,
            }
            return _result_from_mapping(data, adapter="common", message=f"Delay completed after {seconds}s.")
        except Exception as exc:
            return _exception_result("common", exc)


class TrafficAdapter:
    """Run traffic-related phone or server actions."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.tester = TrafficTester(device_id)
        self.running_actions: list[str] = []
        self.explicit_sessions: dict[str, str] = {}

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) in {
            "phone_ping",
            "phone_uplink_iperf",
            "phone_uplink_iperf_start",
            "phone_uplink_iperf_stop",
            "phone_downlink_receive",
            "phone_downlink_receive_start",
            "phone_downlink_receive_stop",
            "phone_airplane_mode",
            "phone_airplane_mode_off",
            "phone_airplane_mode_on",
            "phone_airplane_cycle",
            "stop_phone_traffic",
        }

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            params = dict(step.parameters)
            operation = step.action or step.kind
            if operation == "phone_ping":
                host = str(params.get("host") or "")
                count = int(params.get("count") or 0)
                if hasattr(self.tester, "ping_test"):
                    data = self.tester.ping_test(host, count)
                else:
                    data = self.tester.start_ping_test(host, count)
                return _result_from_mapping(data, adapter="traffic", message="Phone ping completed.")
            if operation in {"phone_airplane_mode_off", "phone_airplane_mode_on"}:
                enabled = operation == "phone_airplane_mode_on"
                data = self.tester.set_airplane_mode(enabled)
                return _result_from_mapping(data, adapter="traffic", message="Phone airplane mode updated.")
            if operation == "phone_airplane_cycle":
                detach_wait_seconds = max(0, int(params.get("detach_wait_seconds") or 0))
                attach_wait_seconds = max(0, int(params.get("attach_wait_seconds") or 0))
                detach = self.tester.set_airplane_mode(True)
                time.sleep(detach_wait_seconds)
                attach = self.tester.set_airplane_mode(False)
                time.sleep(attach_wait_seconds)
                success = bool(detach.get("success", True)) and bool(attach.get("success", True))
                data = {
                    "success": success,
                    "operation": "phone_airplane_cycle",
                    "command": "phone airplane cycle",
                    "results": [
                        {"phase": "detach", "wait_seconds": detach_wait_seconds, **detach},
                        {"phase": "attach", "wait_seconds": attach_wait_seconds, **attach},
                    ],
                }
                return _result_from_mapping(data, adapter="traffic", message="Phone airplane cycle completed.")
            if operation in {"phone_uplink_iperf", "phone_uplink_iperf_start"}:
                arguments = _phone_iperf_arguments(operation, params)
                action = "phone_uplink_iperf"
                if step.action:
                    replacement_result = self._replace_explicit_session("phone_uplink_iperf")
                    if replacement_result is not None:
                        return replacement_result
                data = self.tester.start_device_iperf_command(action, arguments)
                if data.get("success"):
                    if step.action:
                        self.explicit_sessions["phone_uplink_iperf"] = action
                    else:
                        self.running_actions.append(action)
                return _result_from_mapping(data, adapter="traffic", message="Phone uplink iperf started.")
            if operation in {"phone_downlink_receive", "phone_downlink_receive_start"}:
                action = "phone_downlink_receive"
                if step.action:
                    replacement_result = self._replace_explicit_session("phone_downlink_receive")
                    if replacement_result is not None:
                        return replacement_result
                data = self.tester.start_device_iperf_command(action, _phone_iperf_arguments(operation, params))
                if data.get("success"):
                    if step.action:
                        self.explicit_sessions["phone_downlink_receive"] = action
                    else:
                        self.running_actions.append(action)
                return _result_from_mapping(data, adapter="traffic", message="Phone downlink receiver started.")
            if operation == "phone_uplink_iperf_stop":
                return self._stop_explicit_session("phone_uplink_iperf")
            if operation == "phone_downlink_receive_stop":
                return self._stop_explicit_session("phone_downlink_receive")
            if operation == "stop_phone_traffic":
                stopped = []
                success = True
                while self.running_actions:
                    action = self.running_actions[-1]
                    result = self.tester.stop_device_iperf_command(action)
                    stopped.append(result)
                    if bool(result.get("success", True)):
                        self.running_actions.pop()
                    else:
                        success = False
                        break
                while self.explicit_sessions:
                    key, action = next(reversed(self.explicit_sessions.items()))
                    result = self.tester.stop_device_iperf_command(action)
                    stopped.append(result)
                    if bool(result.get("success", True)):
                        self.explicit_sessions.pop(key, None)
                    else:
                        success = False
                        break
                data = {"success": success, "stopped": stopped}
                return _result_from_mapping(data, adapter="traffic", message="Phone traffic stopped.")
            return AdapterResult(
                success=False,
                message=f"Unsupported traffic step: {operation}",
                error=_error("UNSUPPORTED_TRAFFIC_STEP", f"Unsupported traffic step: {operation}", "traffic"),
            )
        except Exception as exc:
            return _exception_result("traffic", exc)

    def cleanup_open_explicit_sessions(self) -> list[AdapterResult]:
        return [self._stop_explicit_session(key, cleanup=True) for key in list(self.explicit_sessions)]

    def _replace_explicit_session(self, session_key: str) -> AdapterResult | None:
        old_action = self.explicit_sessions.get(session_key)
        if old_action:
            data = self.tester.stop_device_iperf_command(old_action)
            data["session_key"] = session_key
            if bool(data.get("success", True)):
                self.explicit_sessions.pop(session_key, None)
                return None
            return _result_from_mapping(data, adapter="traffic", message=f"{session_key} replacement stop failed.")
        return None

    def _stop_explicit_session(self, session_key: str, *, cleanup: bool = False) -> AdapterResult:
        action = self.explicit_sessions.get(session_key)
        if not action:
            data = {
                "success": True,
                "skipped": True,
                "warning": f"No open phone session for {session_key}.",
                "session_key": session_key,
            }
            return _result_from_mapping(data, adapter="traffic", message=f"{session_key} stop skipped.")
        data = self.tester.stop_device_iperf_command(action)
        if bool(data.get("success", True)):
            self.explicit_sessions.pop(session_key, None)
        data["session_key"] = session_key
        if cleanup:
            data["warning"] = CLEANUP_WARNING
        return _result_from_mapping(data, adapter="traffic", message=f"{session_key} stopped.")


class BaseWebAdapter:
    """Wrap base-station Web API actions."""

    def __init__(self):
        self.client = BaseWebClient()
        self.capture_session = None
        self.explicit_sessions: dict[str, Any] = {}

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) in {
            "base_web_collect_log",
            "base_web_capture_start",
            "base_web_start_capture",
            "base_web_capture_stop",
        }

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            params = dict(step.parameters)
            client = self._client_for_params(params)
            operation = step.action or step.kind
            if operation == "base_web_collect_log":
                data = client.collect_log(
                    download_dir=params.get("download_dir"),
                )
                data["command"] = f"web collect log from {params.get('web_host') or params.get('host') or 'configured host'}"
            elif operation in {"base_web_capture_start", "base_web_start_capture"}:
                if step.action:
                    old_session = self.explicit_sessions.get("base_web_capture")
                    if old_session:
                        stop_data = self.client.stop_capture(old_session)
                        if bool(stop_data.get("success", True)):
                            self.explicit_sessions.pop("base_web_capture", None)
                        else:
                            return _result_from_mapping(stop_data, adapter="base_web", message="base_web_capture replacement stop failed.")
                session = client.start_capture(
                    select_msg=_base_web_select_msg(params),
                    transmit_ip=params.get("transmit_ip"),
                )
                if step.action:
                    self.explicit_sessions["base_web_capture"] = session
                else:
                    self.capture_session = session
                data = {
                    "success": True,
                    "session": _object_to_dict(session),
                    "action": operation,
                    "command": f"web capture start SelectMsg={session.select_msg} TransmitIp={session.transmit_ip}",
                }
            elif operation == "base_web_capture_stop":
                session = self.explicit_sessions.get("base_web_capture") if step.action else self.capture_session
                if not session:
                    data = {
                        "success": True,
                        "skipped": True,
                        "warning": "No open base Web capture session.",
                        "message": "Base Web capture stop skipped without session.",
                    }
                else:
                    data = self.client.stop_capture(session, download_dir=params.get("download_dir"))
                    data["command"] = f"web capture stop SelectMsg={session.select_msg} TransmitIp=StopTcpdump"
                    if step.action and bool(data.get("success", True)):
                        self.explicit_sessions.pop("base_web_capture", None)
                    if not step.action and bool(data.get("success", True)):
                        self.capture_session = None
            else:
                return AdapterResult(
                    success=False,
                    message=f"Unsupported base Web step: {operation}",
                    error=_error("UNSUPPORTED_BASE_WEB_STEP", f"Unsupported base Web step: {operation}", "base_web"),
                )
            return _result_from_mapping(data, adapter="base_web", message=f"{operation} completed.")
        except Exception as exc:
            return _exception_result("base_web", exc)

    def cleanup_open_explicit_sessions(self) -> list[AdapterResult]:
        session = self.explicit_sessions.get("base_web_capture")
        if not session:
            return []
        data = self.client.stop_capture(session)
        if bool(data.get("success", True)):
            self.explicit_sessions.pop("base_web_capture", None)
        data["session_key"] = "base_web_capture"
        data["warning"] = CLEANUP_WARNING
        return [_result_from_mapping(data, adapter="base_web", message="base_web_capture cleanup completed.")]

    def _client_for_params(self, params: dict[str, Any]):
        if not any(str(key).startswith("web_") for key in params):
            return self.client
        settings = {
            "host": params.get("web_host") or params.get("host") or "",
            "port": int(params.get("web_port") or params.get("port") or 8400),
            "username": params.get("web_username") or params.get("username") or "",
            "password": params.get("web_password") if "web_password" in params else params.get("password", ""),
            "log_download_dir": params.get("download_dir") or params.get("web_log_download_dir") or "",
            "capture_download_dir": params.get("download_dir") or params.get("web_capture_download_dir") or "",
            "capture_signal_enabled": params.get("capture_signal_enabled", True),
            "capture_data_enabled": params.get("capture_data_enabled", False),
            "capture_fapi_interface": params.get("capture_fapi_interface") or "",
        }
        return BaseWebClient(settings)


class SshAdapter:
    """Wrap base-station SSH command streaming."""

    def __init__(self):
        self.client = BaseSshClient()
        self.log_session = None
        self.explicit_sessions: dict[str, Any] = {}

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) in {
            "base_ssh_log_start",
            "base_ssh_output_log",
            "base_ssh_log_stop",
            "base_ssh_command_start",
            "base_ssh_command_stop",
            "base_ssh_command_once",
            "base_ssh_command_repeat",
        }

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            params = dict(step.parameters)
            operation = step.action or step.kind
            if operation in {"base_ssh_log_start", "base_ssh_output_log"}:
                client = self._client_for_params(params)
                if step.action:
                    old_session = self.explicit_sessions.get("base_ssh_log")
                    if old_session:
                        stop_data = self.client.stop_output_log(old_session)
                        if bool(stop_data.get("success", True)):
                            self.explicit_sessions.pop("base_ssh_log", None)
                        else:
                            return _result_from_mapping(stop_data, adapter="ssh", message="base_ssh_log replacement stop failed.")
                session = client.start_output_log(
                    run_id=str(params.get("run_id") or ""),
                    case_name=str(params.get("case_name") or step.step_id),
                )
                if operation == "base_ssh_output_log" and not step.action:
                    data = self.client.stop_output_log(session)
                else:
                    if step.action:
                        self.explicit_sessions["base_ssh_log"] = session
                    else:
                        self.log_session = session
                data = {
                    "success": True,
                    "local_path": getattr(session, "local_path", ""),
                    "started_at": getattr(session, "started_at", ""),
                    "action": operation,
                    "command": str(params.get("ssh_log_command") or getattr(session, "command", "") or ""),
                }
                return _result_from_mapping(data, adapter="ssh", message=f"{operation} completed.")
            if operation == "base_ssh_log_stop":
                session = self.explicit_sessions.get("base_ssh_log") if step.action else self.log_session
                if not session:
                    data = {"success": True, "skipped": True, "message": "SSH log stop skipped without session."}
                else:
                    data = self.client.stop_output_log(session)
                    if step.action and bool(data.get("success", True)):
                        self.explicit_sessions.pop("base_ssh_log", None)
                    if not step.action and bool(data.get("success", True)):
                        self.log_session = None
                return _result_from_mapping(data, adapter="ssh", message="base_ssh_log_stop completed.")
            if operation == "base_ssh_command_start":
                client = self._client_for_params(params)
                session_key = str(params.get("session_key") or "base_ssh_command")
                old_session = self.explicit_sessions.get(session_key)
                if old_session:
                    stop_data = self.client.stop_output_log(old_session)
                    if bool(stop_data.get("success", True)):
                        self.explicit_sessions.pop(session_key, None)
                    else:
                        return _result_from_mapping(stop_data, adapter="ssh", message=f"{session_key} replacement stop failed.")
                session = client.start_command(
                    str(params.get("command") or ""),
                    str(params.get("run_id") or ""),
                    str(params.get("case_name") or step.step_id),
                    str(params.get("label") or session_key),
                )
                self.explicit_sessions[session_key] = session
                data = {
                    "success": True,
                    "local_path": getattr(session, "local_path", ""),
                    "started_at": getattr(session, "started_at", ""),
                    "session_key": session_key,
                    "action": operation,
                    "command": str(params.get("command") or ""),
                }
                return _result_from_mapping(data, adapter="ssh", message=f"{operation} completed.")
            if operation == "base_ssh_command_stop":
                session_key = str(params.get("session_key") or "base_ssh_command")
                return self._stop_explicit_session(session_key)
            if operation == "base_ssh_command_once":
                client = self._client_for_params(params)
                data = client.run_command(str(params.get("command") or ""))
                data["action"] = operation
                return _result_from_mapping(data, adapter="ssh", message=f"{operation} completed.")
            if operation == "base_ssh_command_repeat":
                client = self._client_for_params(params)
                repeat_count = max(0, int(params.get("repeat_count") or 1))
                interval_seconds = max(0.0, float(params.get("interval_seconds") or 0))
                results = []
                success = True
                for index in range(repeat_count):
                    result = client.run_command(str(params.get("command") or ""))
                    results.append(result)
                    if not bool(result.get("success", True)):
                        success = False
                    if index < repeat_count - 1 and interval_seconds:
                        time.sleep(interval_seconds)
                data = {
                    "success": success,
                    "action": operation,
                    "attempt_count": repeat_count,
                    "results": results,
                }
                return _result_from_mapping(data, adapter="ssh", message=f"{operation} completed.")
            if operation != "base_ssh_output_log":
                return AdapterResult(
                    success=False,
                    message=f"Unsupported SSH step: {operation}",
                    error=_error("UNSUPPORTED_SSH_STEP", f"Unsupported SSH step: {operation}", "ssh"),
                )
        except Exception as exc:
            return _exception_result("ssh", exc)

    def cleanup_open_explicit_sessions(self) -> list[AdapterResult]:
        return [self._stop_explicit_session(key, cleanup=True) for key in list(self.explicit_sessions)]

    def _stop_explicit_session(self, session_key: str, *, cleanup: bool = False) -> AdapterResult:
        session = self.explicit_sessions.get(session_key)
        if not session:
            data = {
                "success": True,
                "skipped": True,
                "warning": f"No open SSH session for {session_key}.",
                "session_key": session_key,
            }
            return _result_from_mapping(data, adapter="ssh", message=f"{session_key} stop skipped.")
        data = self.client.stop_output_log(session)
        if bool(data.get("success", True)):
            self.explicit_sessions.pop(session_key, None)
        data["session_key"] = session_key
        if cleanup:
            data["warning"] = CLEANUP_WARNING
        return _result_from_mapping(data, adapter="ssh", message=f"{session_key} stopped.")

    def _client_for_params(self, params: dict[str, Any]):
        if not any(str(key).startswith("ssh_") for key in params):
            return self.client
        settings = {
            "host": params.get("ssh_host") or params.get("host") or "",
            "port": int(params.get("ssh_port") or params.get("port") or 22),
            "username": params.get("ssh_username") or params.get("username") or "",
            "password": params.get("ssh_password") if "ssh_password" in params else params.get("password", ""),
            "log_output_dir": params.get("ssh_log_output_dir") or params.get("log_output_dir") or "",
            "log_command": params.get("ssh_log_command") or params.get("log_command") or "",
            "connect_timeout": int(params.get("ssh_connect_timeout") or params.get("connect_timeout") or 20),
        }
        return BaseSshClient(settings)


class CaptureAdapter:
    """Wrap device tcpdump capture."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.backend = DeviceTcpdumpCaptureBackend()

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) == "capture"

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            params = dict(step.parameters)
            case_dir = params.get("case_dir")
            if not case_dir:
                return AdapterResult(success=True, message="Capture skipped without case_dir.", data={"skipped": True})
            session = start_capture_with_fallback(
                self.backend,
                self.device_id,
                case_dir,
                host=str(params.get("host") or ""),
            )
            record = session.stop()
            data = record if isinstance(record, dict) else _object_to_dict(record)
            return _result_from_mapping(data, adapter="capture", message="Capture completed.")
        except Exception as exc:
            return _exception_result("capture", exc)


class TrafficServerAdapter:
    """Wrap traffic server SSH actions."""

    def __init__(self):
        self.client = TrafficServerClient()
        self.sessions = []
        self.explicit_sessions: dict[str, Any] = {}

    def can_handle(self, step: StepPlan) -> bool:
        return (step.action or step.kind) in {
            "server_downlink_iperf",
            "server_down_ping",
            "server_uplink_receive",
            "traffic_server_downlink_start",
            "traffic_server_downlink_stop",
            "traffic_server_down_ping_start",
            "traffic_server_down_ping_stop",
            "traffic_server_uplink_receive_start",
            "traffic_server_uplink_receive_stop",
            "stop_traffic_server",
        }

    def run_step(self, step: StepPlan) -> AdapterResult:
        try:
            params = dict(step.parameters)
            operation = step.action or step.kind
            explicit_start_keys = {
                "traffic_server_downlink_start": "traffic_server_downlink",
                "traffic_server_down_ping_start": "traffic_server_down_ping",
                "traffic_server_uplink_receive_start": "traffic_server_uplink_receive",
            }
            explicit_stop_keys = {
                "traffic_server_downlink_stop": "traffic_server_downlink",
                "traffic_server_down_ping_stop": "traffic_server_down_ping",
                "traffic_server_uplink_receive_stop": "traffic_server_uplink_receive",
            }
            if operation in explicit_start_keys or operation in {"server_downlink_iperf", "server_down_ping", "server_uplink_receive"}:
                session_key = explicit_start_keys.get(operation)
                if session_key:
                    old_session = self.explicit_sessions.get(session_key)
                    if old_session:
                        stop_data = self.client.stop_command(old_session)
                        if bool(stop_data.get("success", True)):
                            self.explicit_sessions.pop(session_key, None)
                        else:
                            return _result_from_mapping(stop_data, adapter="traffic_server", message=f"{session_key} replacement stop failed.")
                session = self.client.start_command(
                    step.kind,
                    _traffic_server_command(operation, params),
                    str(params.get("run_id") or ""),
                    str(params.get("case_name") or step.step_id),
                )
                if operation in explicit_start_keys:
                    self.explicit_sessions[session_key] = session
                else:
                    self.sessions.append(session)
                data = {
                    "success": True,
                    "action": step.kind,
                    "command": session.command,
                    "local_path": session.local_path,
                    "started_at": session.started_at,
                }
                return _result_from_mapping(data, adapter="traffic_server", message=f"{step.kind} started.")
            if operation in explicit_stop_keys:
                return self._stop_explicit_session(explicit_stop_keys[operation])
            if operation == "stop_traffic_server":
                stopped = []
                success = True
                while self.sessions:
                    session = self.sessions[-1]
                    result = self.client.stop_command(session)
                    stopped.append(result)
                    if bool(result.get("success", True)):
                        self.sessions.pop()
                    else:
                        success = False
                        break
                while self.explicit_sessions:
                    key, session = next(reversed(self.explicit_sessions.items()))
                    result = self.client.stop_command(session)
                    stopped.append(result)
                    if bool(result.get("success", True)):
                        self.explicit_sessions.pop(key, None)
                    else:
                        success = False
                        break
                data = {"success": success, "stopped": stopped}
                return _result_from_mapping(data, adapter="traffic_server", message="Traffic server stopped.")
            return AdapterResult(
                success=False,
                message=f"Unsupported traffic server step: {operation}",
                error=_error(
                    "UNSUPPORTED_TRAFFIC_SERVER_STEP",
                    f"Unsupported traffic server step: {operation}",
                    "traffic_server",
                ),
            )
        except Exception as exc:
            return _exception_result("traffic_server", exc)

    def cleanup_open_explicit_sessions(self) -> list[AdapterResult]:
        return [self._stop_explicit_session(key, cleanup=True) for key in list(self.explicit_sessions)]

    def _stop_explicit_session(self, session_key: str, *, cleanup: bool = False) -> AdapterResult:
        session = self.explicit_sessions.get(session_key)
        if not session:
            data = {
                "success": True,
                "skipped": True,
                "warning": f"No open traffic server session for {session_key}.",
                "session_key": session_key,
            }
            return _result_from_mapping(data, adapter="traffic_server", message=f"{session_key} stop skipped.")
        data = self.client.stop_command(session)
        if bool(data.get("success", True)):
            self.explicit_sessions.pop(session_key, None)
        data["session_key"] = session_key
        if cleanup:
            data["warning"] = CLEANUP_WARNING
        return _result_from_mapping(data, adapter="traffic_server", message=f"{session_key} stopped.")


class AdapterRegistry:
    """Small compatibility registry for adapter smoke checks and direct lookup."""

    def __init__(self, device_id: str = "", adapters: dict[str, Any] | None = None):
        self.adapters = adapters or build_default_adapters(device_id)

    def get(self, name: str) -> Any:
        return self.adapters[name]


def build_default_adapters(device_id: str) -> dict[str, Any]:
    """Build default real adapters for one device."""

    return {
        "snapshot": SnapshotAdapter(device_id),
        "common": CommonAdapter(),
        "traffic": TrafficAdapter(device_id),
        "base_web": BaseWebAdapter(),
        "ssh": SshAdapter(),
        "capture": CaptureAdapter(device_id),
        "traffic_server": TrafficServerAdapter(),
    }


def _result_from_mapping(data: dict[str, Any], *, adapter: str, message: str) -> AdapterResult:
    success = bool(data.get("success", True))
    error = None
    if not success:
        error = _error(
            code=f"{adapter.upper()}_FAILED",
            message=str(data.get("error") or data.get("message") or message),
            adapter=adapter,
            details=data,
        )
    artifacts = _artifacts_from_mapping(data)
    metrics = {
        key: value
        for key, value in data.items()
        if key.endswith("_count") or key.endswith("_ms") or key.endswith("_mbps") or key in {"packet_loss", "loss_percent"}
    }
    return AdapterResult(
        success=success,
        message=str(data.get("message") or message),
        metrics=metrics,
        artifacts=artifacts,
        data=data,
        error=error,
    )


def _artifacts_from_mapping(data: dict[str, Any]) -> list[Artifact]:
    artifacts: list[Artifact] = []
    for key in ("local_path", "local_log_path", "local_pcap_path", "output_path", "downloaded_path"):
        value = data.get(key)
        if value:
            artifacts.append(Artifact(kind=key, path=str(value)))
    return artifacts


def _base_web_select_msg(params: dict[str, Any]) -> str:
    planes = []
    if bool(params.get("capture_signal_enabled", True)):
        planes.append("CP")
    if bool(params.get("capture_data_enabled", False)):
        planes.append("UP")
    interface = str(params.get("capture_fapi_interface") or "").strip()
    if interface and interface not in {"无", "鏃?"}:
        planes.append(interface)
    return ",".join(planes) or str(params.get("select_msg") or "CP")


def _traffic_server_command(operation: str, params: dict[str, Any]) -> str:
    command = str(params.get("command") or "").strip()
    if command:
        return command
    if operation in {"traffic_server_downlink_start", "server_downlink_iperf"}:
        target = str(params.get("server_downlink_target") or params.get("target") or "").strip()
        duration = int(params.get("server_downlink_duration") or params.get("iperf_duration") or 60000)
        bandwidth = str(params.get("server_downlink_bandwidth") or params.get("iperf_bandwidth") or "250m")
        packet_len = int(params.get("server_downlink_packet_len") or params.get("packet_len") or 1300)
        port = int(params.get("server_downlink_port") or params.get("iperf_port") or 6011)
        return f"iperf -u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
    if operation in {"traffic_server_uplink_receive_start", "server_uplink_receive"}:
        port = int(params.get("server_uplink_listen_port") or params.get("iperf_port") or 7011)
        return f"iperf -u -s -i 1 -p {port}"
    if operation == "traffic_server_down_ping_start":
        target = str(params.get("ping_target") or params.get("server_ping_target") or "").strip()
        count = int(params.get("ping_count") or 0)
        if target and count > 0:
            return f"ping {target} -n {count}"
        if target:
            return f"ping {target}"
    return command


def _phone_iperf_arguments(operation: str, params: dict[str, Any]) -> str:
    arguments = str(params.get("arguments") or "").strip()
    if arguments:
        return arguments
    if operation in {"phone_downlink_receive", "phone_downlink_receive_start"}:
        port = int(params.get("phone_downlink_listen_port") or params.get("iperf_port") or 6011)
        return f"-u -s -i 1 -p {port}"
    if operation in {"phone_uplink_iperf", "phone_uplink_iperf_start"}:
        target = str(params.get("phone_uplink_target") or params.get("target") or "").strip()
        duration = int(params.get("phone_uplink_duration") or params.get("iperf_duration") or 6000)
        bandwidth = str(params.get("phone_uplink_bandwidth") or params.get("iperf_bandwidth") or "120m")
        packet_len = int(params.get("phone_uplink_packet_len") or params.get("packet_len") or 1350)
        port = int(params.get("phone_uplink_port") or params.get("iperf_port") or 7011)
        return f"-u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
    return arguments


def _exception_result(adapter: str, exc: Exception) -> AdapterResult:
    return AdapterResult(
        success=False,
        message=str(exc),
        error=_error(
            code=f"{adapter.upper()}_EXCEPTION",
            message=str(exc),
            adapter=adapter,
            details={"exception_type": type(exc).__name__},
        ),
    )


def _error(
    code: str,
    message: str,
    adapter: str,
    *,
    details: dict[str, Any] | None = None,
) -> AdapterError:
    return AdapterError(
        code=code,
        message=message,
        adapter=adapter,
        recoverable=False,
        details=details or {},
    )


def _object_to_dict(value) -> dict[str, Any]:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"success": True, "value": str(value)}
