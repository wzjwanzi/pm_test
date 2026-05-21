"""Traffic and ping test helpers."""
from __future__ import annotations

import re
import shlex
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict

from app_settings import (
    build_device_iperf_arguments,
    build_device_iperf_command,
    build_device_traffic_iperf_command,
    get_device_iperf_binary,
    get_device_iperf_log,
    get_device_iperf_tool,
    get_ping_settings,
)
import config
from network.iperf_parser import parse_iperf_text
from network.network_utils import get_active_interface, get_interface_stats, pick_active_interface
from utils.adb_utils import adb_shell, run_adb


class TrafficTester:
    """Used for traffic-related testing on a device."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.last_error = ""

    def get_traffic_stats(self) -> Dict:
        """Return current RX/TX counters from the active interface."""
        try:
            active_interface = get_active_interface(self.device_id)
            rx_bytes = active_interface.rx_bytes
            tx_bytes = active_interface.tx_bytes

            return {
                "success": True,
                "interface": active_interface.name,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_mb": round(rx_bytes / 1024 / 1024, 2),
                "tx_mb": round(tx_bytes / 1024 / 1024, 2),
                "total_mb": round((rx_bytes + tx_bytes) / 1024 / 1024, 2),
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
            }

    def sample_downlink_traffic(self, sample_seconds: float | None = None) -> Dict:
        """Measure current downlink traffic by sampling RX bytes on the active interface."""
        sample_seconds = sample_seconds or config.TRAFFIC_MONITOR_SAMPLE_SECONDS

        try:
            if sample_seconds <= 0:
                raise ValueError("sample_seconds must be greater than zero.")

            before_stats = {item.name: item for item in get_interface_stats(self.device_id)}
            before_active = pick_active_interface(before_stats.values())
            if not before_active:
                raise RuntimeError("Could not detect an active network interface before sampling.")

            time.sleep(sample_seconds)

            after_stats = {item.name: item for item in get_interface_stats(self.device_id)}
            after_active = after_stats.get(before_active.name) or pick_active_interface(after_stats.values())
            if not after_active:
                raise RuntimeError("Could not detect an active network interface after sampling.")

            before_interface = before_stats.get(after_active.name) or before_active
            rx_delta_bytes = max(after_active.rx_bytes - before_interface.rx_bytes, 0)
            tx_delta_bytes = max(after_active.tx_bytes - before_interface.tx_bytes, 0)

            return {
                "success": True,
                "mode": "downlink_monitor",
                "timestamp": datetime.now().isoformat(),
                "interface": after_active.name,
                "sample_seconds": sample_seconds,
                "rx_bytes": after_active.rx_bytes,
                "tx_bytes": after_active.tx_bytes,
                "rx_mb": round(after_active.rx_bytes / 1024 / 1024, 2),
                "tx_mb": round(after_active.tx_bytes / 1024 / 1024, 2),
                "total_mb": round((after_active.rx_bytes + after_active.tx_bytes) / 1024 / 1024, 2),
                "rx_delta_bytes": rx_delta_bytes,
                "tx_delta_bytes": tx_delta_bytes,
                "rx_delta_mb": round(rx_delta_bytes / 1024 / 1024, 4),
                "tx_delta_mb": round(tx_delta_bytes / 1024 / 1024, 4),
                "rx_mbps": round((rx_delta_bytes * 8) / sample_seconds / 1024 / 1024, 2),
                "tx_mbps": round((tx_delta_bytes * 8) / sample_seconds / 1024 / 1024, 2),
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
            }

    def start_download_test(self, url: str = "", duration: int = 60) -> bool:
        """Compatibility shim for legacy routes."""
        del url, duration
        result = self.sample_downlink_traffic(config.TRAFFIC_MONITOR_SAMPLE_SECONDS)
        if result.get("success"):
            self.last_error = ""
            return True
        self.last_error = result.get("error", "Downlink sampling failed.")
        return False

    def start_upload_test(self, url: str = "", file_size_mb: int = 0, duration: int = 0) -> bool:
        """Compatibility shim for legacy routes."""
        del url, file_size_mb, duration
        result = self.start_uplink_iperf_test()
        if result.get("success"):
            self.last_error = ""
            return True
        self.last_error = result.get("error", "Uplink iperf test failed.")
        return False

    def start_uplink_iperf_test(self) -> Dict:
        """Run the fixed device-side iperf uplink command through adb shell."""
        try:
            self.last_error = ""
            iperf_arguments = build_device_iperf_arguments()
            iperf_command = build_device_iperf_command()
            iperf_binary = get_device_iperf_binary()
            iperf_log = get_device_iperf_log()
            iperf_tool = get_device_iperf_tool()
            self._ensure_device_iperf_binary(iperf_binary, iperf_tool)
            self._stop_device_iperf_processes()
            self._adb_shell_script(
                f"rm -f {shlex.quote(iperf_log)}",
                timeout=20,
            )
            self._adb_shell_script(
                (
                    f"{shlex.quote(iperf_binary)} "
                    f"{iperf_arguments} > {shlex.quote(iperf_log)} 2>&1 &"
                ),
                check=True,
                timeout=20,
            )
            time.sleep(config.MAGIC_IPERF_RESULT_WAIT_SECONDS)

            status = self.get_uplink_iperf_status()
            status["message"] = f"adb shell {iperf_tool} uplink test started."
            status["command"] = iperf_command
            return status
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
                "command": build_device_iperf_command(),
            }

    def get_uplink_iperf_status(self) -> Dict:
        """Read the current fixed device-side iperf uplink result from the device log."""
        try:
            result_text = self._read_uplink_log()
            parsed_output = self._parse_iperf_output(result_text)
            is_running = self._is_device_iperf_running()
            app_open = is_running or bool(parsed_output["line_count"])
            iperf_tool = get_device_iperf_tool()
            iperf_binary = get_device_iperf_binary()

            return {
                "success": True,
                "mode": f"adb_shell_{iperf_tool}_uplink",
                "app_open": app_open,
                "running": is_running,
                "command": build_device_iperf_command(),
                "binary": iperf_binary,
                "tool": iperf_tool,
                **parsed_output,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
                "command": build_device_iperf_command(),
            }

    def stop_uplink_iperf_test(self) -> Dict:
        """Stop the current fixed device-side iperf uplink process."""
        try:
            iperf_tool = get_device_iperf_tool()
            self._stop_device_iperf_processes()
            self._adb_shell_script(f"rm -f {shlex.quote(get_device_iperf_log())}", timeout=20)
            time.sleep(0.5)
            return {
                "success": True,
                "mode": f"adb_shell_{iperf_tool}_uplink",
                "message": f"adb shell {iperf_tool} uplink test stopped.",
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
            }

    def start_device_iperf_command(self, action: str, arguments: str) -> Dict:
        """Start a device-side iperf command through adb shell and keep its log on the device."""
        try:
            self.last_error = ""
            iperf_binary = get_device_iperf_binary()
            iperf_tool = get_device_iperf_tool()
            self._ensure_device_iperf_binary(iperf_binary, iperf_tool)
            remote_log = self._traffic_action_log(action)
            self._adb_shell_script(f"rm -f {shlex.quote(remote_log)}", timeout=20)
            self._adb_shell_script(
                (
                    f"{shlex.quote(iperf_binary)} {arguments} "
                    f"> {shlex.quote(remote_log)} 2>&1 &"
                ),
                check=True,
                timeout=20,
            )
            time.sleep(config.MAGIC_IPERF_RESULT_WAIT_SECONDS)
            status = self.get_device_iperf_status(action, arguments)
            status["message"] = f"adb shell {iperf_tool} command started."
            return status
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
                "action": action,
                "command": build_device_traffic_iperf_command(arguments),
            }

    def get_device_iperf_status(self, action: str, arguments: str = "") -> Dict:
        """Read a device-side traffic iperf log and running state."""
        try:
            remote_log = self._traffic_action_log(action)
            result_text = self._read_device_log(remote_log, config.DEVICE_IPERF3_STATUS_TAIL_LINES)
            parsed_output = self._parse_iperf_output(result_text)
            is_running = self._is_device_iperf_running()
            return {
                "success": True,
                "mode": f"adb_shell_{get_device_iperf_tool()}_{action}",
                "action": action,
                "running": is_running,
                "command": build_device_traffic_iperf_command(arguments) if arguments else "",
                "binary": get_device_iperf_binary(),
                "tool": get_device_iperf_tool(),
                "remote_log": remote_log,
                **parsed_output,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
                "action": action,
            }

    def stop_device_iperf_command(self, action: str) -> Dict:
        """Stop device-side iperf and return the last log preview."""
        try:
            status = self.get_device_iperf_status(action)
            self._stop_device_iperf_processes()
            time.sleep(0.5)
            status["running_after_stop"] = self._is_device_iperf_running()
            status["message"] = f"adb shell {get_device_iperf_tool()} command stopped."
            return status
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc),
                "action": action,
            }

    def start_ping_test(self, host: str = "", count: int = 0) -> Dict:
        """Run ping on the device through adb shell and return parsed latency samples."""
        ping_settings = get_ping_settings()
        target_host = (host or ping_settings["host"] or config.PING_APP_FIXED_HOST).strip()
        target_count = int(count or ping_settings["count"] or config.PING_APP_FIXED_COUNT)
        result = self._run_adb_shell_ping(target_host, target_count)
        if not result.get("success"):
            self.last_error = str(result.get("error") or "Ping test failed.")
        return result

    def set_airplane_mode(self, enabled: bool) -> Dict:
        """Toggle device airplane mode through adb shell."""
        action = "enable" if enabled else "disable"
        state_value = "1" if enabled else "0"
        state_text = "true" if enabled else "false"
        scripts = [
            f"cmd connectivity airplane-mode {action}",
            f"settings put global airplane_mode_on {state_value}",
            f"am broadcast -a android.intent.action.AIRPLANE_MODE --ez state {state_text}",
        ]
        commands = []
        try:
            self.last_error = ""
            for script in scripts:
                result = self._adb_shell_script(script, check=False, timeout=20)
                commands.append(
                    {
                        "command": self._adb_display_command(script),
                        "stdout": (result.stdout or "").strip(),
                        "stderr": (result.stderr or "").strip(),
                        "exit_status": result.returncode,
                    }
                )
            observed = self._read_airplane_mode_state()
            success = any(item["exit_status"] == 0 for item in commands)
            if observed in {"0", "1"}:
                success = success and observed == state_value
            if not success:
                expected = "enabled" if enabled else "disabled"
                raise RuntimeError(
                    f"Airplane mode was not {expected} on selected device {self.device_id}. "
                    f"Expected airplane_mode_on={state_value}, observed={observed or 'unknown'}."
                )
            return {
                "success": True,
                "mode": "airplane_mode_on" if enabled else "airplane_mode_off",
                "enabled": enabled,
                "command": commands[-1]["command"],
                "commands": commands,
                "observed_airplane_mode_on": observed,
                "message": "Airplane mode enabled." if enabled else "Airplane mode disabled.",
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "mode": "airplane_mode_on" if enabled else "airplane_mode_off",
                "enabled": enabled,
                "error": str(exc),
                "commands": commands,
            }

    def _read_airplane_mode_state(self) -> str:
        result = run_adb(
            ["shell", "settings", "get", "global", "airplane_mode_on"],
            device_id=self.device_id,
            check=False,
            timeout=10,
        )
        return (result.stdout or "").strip()

    def _adb_display_command(self, script: str) -> str:
        prefix = f"adb -s {self.device_id}" if self.device_id else "adb"
        return f"{prefix} shell {script}"

    def _run_ping_app_test(self, host: str, count: int) -> str:
        if not self.device_id:
            raise RuntimeError("Missing device_id.")

        self.last_error = ""
        self._restart_ping_app()
        ui_root = self._wait_for_ping_screen()
        ui_root = self._set_ping_host_input(host, initial_root=ui_root)
        self._tap(*self._get_element_center(ui_root, config.PING_APP_START_BUTTON_RESOURCE_ID))
        time.sleep(max(5, min(count, 8)))
        try:
            return self._wait_for_ping_result(host, count)
        finally:
            self._stop_ping_app_if_running()

    def _wait_for_ping_screen(self, timeout_seconds: int = 12) -> ET.Element:
        deadline = time.time() + timeout_seconds
        last_error = ""
        while time.time() < deadline:
            try:
                root = self._dump_ui()
                if self._get_root_package(root) != config.PING_APP_PACKAGE:
                    time.sleep(0.8)
                    continue
                self._get_element_bounds(root, config.PING_APP_HOST_RESOURCE_ID)
                self._get_element_bounds(root, config.PING_APP_START_BUTTON_RESOURCE_ID)
                return root
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.8)

        raise RuntimeError(last_error or "Ping app screen not ready.")

    def _set_ping_host_input(self, host: str, initial_root: ET.Element | None = None) -> ET.Element:
        last_seen_host = ""
        for _ in range(4):
            try:
                ui_root = initial_root if initial_root is not None else self._wait_for_ping_screen()
                initial_root = None
                current_host = self._read_ping_host_value(ui_root)
                if current_host:
                    last_seen_host = current_host
                if current_host == host:
                    return ui_root

                host_center = self._get_element_center(ui_root, config.PING_APP_HOST_RESOURCE_ID)
                self._tap(*host_center)
                time.sleep(0.3)
                self._replace_ping_host_input(current_host, host)
                self._dismiss_ping_keyboard()
                verified_root = self._wait_for_ping_screen(timeout_seconds=8)
                actual_host = self._read_ping_host_value(verified_root)
                if actual_host:
                    last_seen_host = actual_host
                if actual_host == host:
                    return verified_root
            except Exception:
                pass
            time.sleep(0.8)

        if last_seen_host:
            raise RuntimeError(
                f"Ping host input mismatch. Expected {host}, actual {last_seen_host}."
            )
        raise RuntimeError(f"Ping host input mismatch. Expected {host}.")

    def _read_ping_host_value(self, root: ET.Element) -> str:
        host_value = self._get_element_text(root, config.PING_APP_HOST_RESOURCE_ID).strip()
        if host_value:
            return host_value
        spinner_value = self._get_element_text(root, "android:id/text1").strip()
        return spinner_value

    def _dismiss_ping_keyboard(self) -> None:
        adb_shell(self.device_id, ["input", "keyevent", "4"], check=True, timeout=10)
        time.sleep(0.8)

    def _replace_ping_host_input(self, existing_text: str, target_host: str) -> None:
        self._clear_ping_host_input(existing_text)
        time.sleep(0.3)
        if self._paste_ping_host_input(target_host):
            time.sleep(0.5)
            return
        adb_shell(self.device_id, ["input", "text", target_host], check=True, timeout=20)
        time.sleep(0.5)

    def _paste_ping_host_input(self, target_host: str) -> bool:
        try:
            adb_shell(
                self.device_id,
                ["cmd", "clipboard", "set", "text", target_host],
                check=True,
                timeout=15,
            )
            time.sleep(0.2)
            adb_shell(self.device_id, ["input", "keyevent", "279"], check=True, timeout=10)
            return True
        except Exception:
            return False

    def _restart_ping_app(self) -> None:
        adb_shell(
            self.device_id,
            ["am", "force-stop", config.PING_APP_PACKAGE],
            check=True,
            timeout=20,
        )
        time.sleep(0.5)
        adb_shell(
            self.device_id,
            ["am", "start", "-n", f"{config.PING_APP_PACKAGE}/{config.PING_APP_ACTIVITY}"],
            check=True,
            timeout=20,
        )

    def _restart_magic_iperf(self) -> None:
        adb_shell(
            self.device_id,
            ["am", "force-stop", config.MAGIC_IPERF_PACKAGE],
            check=True,
            timeout=20,
        )
        time.sleep(0.5)
        adb_shell(
            self.device_id,
            ["am", "start", "-n", f"{config.MAGIC_IPERF_PACKAGE}/{config.MAGIC_IPERF_ACTIVITY}"],
            check=True,
            timeout=20,
        )

    def _ensure_device_iperf_binary(self, binary_path: str, tool_name: str) -> None:
        binary = shlex.quote(binary_path)
        self._adb_shell_script(
            (
                f"if [ ! -f {binary} ]; then "
                f"echo 'Missing {tool_name} binary: {binary_path}'; exit 1; "
                f"fi; chmod 755 {binary}; if [ ! -x {binary} ]; then "
                f"echo '{tool_name} binary is not executable: {binary_path}'; exit 1; "
                "fi"
            ),
            check=True,
            timeout=20,
        )

    def _read_uplink_log(self) -> str:
        return self._read_device_log(get_device_iperf_log(), config.DEVICE_IPERF3_STATUS_TAIL_LINES)

    def _read_device_log(self, remote_log: str, tail_lines: int) -> str:
        result = self._adb_shell_script(
            f"tail -n {int(tail_lines)} {shlex.quote(remote_log)} 2>/dev/null || true",
            timeout=20,
        )
        return result.stdout.replace("\x00", "").strip()

    def _traffic_action_log(self, action: str) -> str:
        safe_action = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(action or "traffic"))[:60]
        return f"/sdcard/{safe_action}.log"

    def _is_device_iperf_running(self) -> bool:
        result = self._adb_shell_script(
            f"ps -A | grep '{self._device_iperf_process_pattern()}'",
            timeout=20,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def _stop_device_iperf_processes(self) -> None:
        self._adb_shell_script(
            (
                f"for p in $(ps -A | grep '{self._device_iperf_process_pattern()}' "
                "| awk '{print $2}'); do kill $p; done"
            ),
            timeout=20,
        )

    def _device_iperf_process_pattern(self) -> str:
        return "[i]perf3" if get_device_iperf_tool() == "iperf3" else "[i]perf"

    def _adb_shell_script(self, script: str, *, check: bool = False, timeout: int = 30):
        return run_adb(
            ["shell", f"sh -c {shlex.quote(script)}"],
            device_id=self.device_id,
            check=check,
            timeout=timeout,
        )

    def _clear_ping_host_input(self, existing_text: str = "") -> None:
        clear_count = max(len(existing_text) + 4, config.PING_APP_BACKSPACE_COUNT)
        adb_shell(self.device_id, ["input", "keyevent", "123"], check=True, timeout=10)
        time.sleep(0.2)
        for _ in range(clear_count):
            adb_shell(self.device_id, ["input", "keyevent", "67"], check=True, timeout=10)
            time.sleep(0.12)
        adb_shell(self.device_id, ["input", "keyevent", "122"], check=True, timeout=10)
        time.sleep(0.2)
        for _ in range(clear_count * 2):
            adb_shell(self.device_id, ["input", "keyevent", "112"], check=True, timeout=10)
            time.sleep(0.05)
        adb_shell(self.device_id, ["input", "keyevent", "123"], check=True, timeout=10)
        time.sleep(0.2)
        for _ in range(clear_count * 2):
            adb_shell(self.device_id, ["input", "keyevent", "67"], check=True, timeout=10)
            time.sleep(0.05)

    def _tap(self, x: int, y: int) -> None:
        adb_shell(self.device_id, ["input", "tap", str(x), str(y)], check=True, timeout=10)

    def _dump_ui(self) -> ET.Element:
        remote_path = "/storage/emulated/0/window_dump.xml"
        last_error = ""
        for _ in range(3):
            try:
                with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix="ui_dump_") as temp_dir:
                    local_path = Path(temp_dir) / "window_dump.xml"
                    adb_shell(self.device_id, ["uiautomator", "dump"], check=True, timeout=20)
                    run_adb(
                        ["pull", remote_path, str(local_path)],
                        device_id=self.device_id,
                        check=True,
                        timeout=20,
                    )
                    return ET.parse(local_path).getroot()
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.5)

        raise RuntimeError(last_error or "Failed to dump Ping app UI.")

    def _get_root_package(self, root: ET.Element) -> str:
        for node in root.iter("node"):
            package_name = node.attrib.get("package", "")
            if package_name:
                return package_name
        return ""

    def _get_element_center(self, root: ET.Element, resource_id: str) -> tuple[int, int]:
        x1, y1, x2, y2 = self._get_element_bounds(root, resource_id)
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _get_element_bounds(self, root: ET.Element, resource_id: str) -> tuple[int, int, int, int]:
        for node in root.iter("node"):
            if node.attrib.get("resource-id") != resource_id:
                continue

            bounds = node.attrib.get("bounds", "")
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not match:
                break
            return tuple(int(value) for value in match.groups())

        raise RuntimeError(f"Could not find UI element: {resource_id}")

    def _get_optional_element_center(self, root: ET.Element, resource_id: str) -> tuple[int, int] | None:
        try:
            return self._get_element_center(root, resource_id)
        except Exception:
            return None

    def _get_text_center(self, root: ET.Element, expected_text: str) -> tuple[int, int]:
        for node in root.iter("node"):
            if node.attrib.get("text") != expected_text:
                continue

            bounds = node.attrib.get("bounds", "")
            match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
            if not match:
                break
            x1, y1, x2, y2 = (int(value) for value in match.groups())
            return ((x1 + x2) // 2, (y1 + y2) // 2)

        raise RuntimeError(f"Could not find UI text: {expected_text}")

    def _get_element_text(self, root: ET.Element, resource_id: str) -> str:
        for node in root.iter("node"):
            if node.attrib.get("resource-id") == resource_id:
                return node.attrib.get("text", "")
        return ""

    def _wait_for_ping_result(self, host: str, count: int) -> str:
        deadline = time.time() + max(config.PING_APP_CAPTURE_WAIT_SECONDS, count * 4 + 10)
        last_text = ""
        stable_rounds = 0
        while time.time() < deadline:
            try:
                result_root = self._dump_ui()
                result_text = self._extract_ping_result_text(result_root).strip()
                if result_text:
                    stable_rounds = stable_rounds + 1 if result_text == last_text else 0
                    last_text = result_text
                    lower_text = result_text.lower()
                    sample_count = len(self._parse_ping_samples(result_text, host, count))
                    if sample_count >= count:
                        return result_text
                    if "packet loss" in lower_text and stable_rounds >= 2:
                        return result_text
            except Exception:
                pass
            time.sleep(1)

        if last_text:
            return last_text
        raise RuntimeError("Ping app did not produce visible result text.")

    def _stop_ping_app_if_running(self) -> None:
        for _ in range(2):
            try:
                result_root = self._dump_ui()
                stop_center = self._get_optional_element_center(
                    result_root,
                    config.PING_APP_START_BUTTON_RESOURCE_ID,
                )
                if not stop_center:
                    return
                self._tap(*stop_center)
                time.sleep(0.5)
                return
            except Exception:
                time.sleep(0.5)

    def _build_ping_failure_message(self, result_text: str, host: str, count: int) -> str:
        lower_text = result_text.lower()
        for marker in (
            "network is unreachable",
            "destination host unreachable",
            "unknown host",
            "no address associated with hostname",
        ):
            if marker in lower_text:
                return f"Ping app reported: {self._first_result_line(result_text)}"

        sample_count = len(self._parse_ping_samples(result_text, host, count))
        if result_text.strip():
            return (
                f"Ping app returned only {sample_count} results; expected {count}. "
                f"Last output: {self._first_result_line(result_text)}"
            )
        return f"Ping app returned only {sample_count} results; expected {count}."

    def _first_result_line(self, result_text: str) -> str:
        for line in result_text.splitlines():
            normalized = line.strip()
            if normalized:
                return normalized
        return "empty"

    def _is_transient_ping_error(self, error_text: str) -> bool:
        normalized = (error_text or "").lower()
        return any(
            marker in normalized
            for marker in (
                "could not find ui element",
                "screen not ready",
                "failed to dump ping app ui",
                "adb",
            )
        )

    def _extract_ping_result_text(self, root: ET.Element) -> str:
        candidates: list[str] = []
        for node in root.iter("node"):
            text_value = (node.attrib.get("text") or "").strip()
            desc_value = (node.attrib.get("content-desc") or "").strip()
            if text_value:
                candidates.append(text_value)
            if desc_value:
                candidates.append(desc_value)

        result = "\n".join(
            item
            for item in candidates
            if (
                "bytes from" in item.lower()
                or "icmp_seq" in item.lower()
                or "time=" in item.lower()
                or "packet loss" in item.lower()
                or "timed out" in item.lower()
                or "unreachable" in item.lower()
                or "unknown host" in item.lower()
                or item.count("64 bytes from") >= 1
            )
        )
        if result:
            return result

        return self._get_element_text(root, config.PING_APP_RESULT_RESOURCE_ID)

    def _parse_iperf_output(self, result_text: str) -> Dict:
        return parse_iperf_text(result_text)

    def _parse_ping_samples(self, result_text: str, host: str, limit: int) -> list[Dict]:
        samples: list[Dict] = []
        exact_host_pattern = re.compile(
            rf"bytes from {re.escape(host)}:.*?time[=<]([0-9.]+)\s*ms",
            re.IGNORECASE,
        )
        latency_pattern = re.compile(r"\btime[=<]([0-9.]+)\s*ms", re.IGNORECASE)

        for line in result_text.splitlines():
            normalized = line.strip()
            if not normalized:
                continue

            match = exact_host_pattern.search(normalized) or latency_pattern.search(normalized)
            if match:
                samples.append(
                    {
                        "seq": len(samples) + 1,
                        "status": "ok",
                        "latency_ms": float(match.group(1)),
                        "line": normalized,
                    }
                )
            elif "request timed out" in normalized.lower() or "timeout" in normalized.lower():
                samples.append(
                    {
                        "seq": len(samples) + 1,
                        "status": "timeout",
                        "latency_ms": None,
                        "line": normalized,
                    }
                )
            else:
                continue

            if len(samples) >= limit:
                break

        return samples

    def _run_adb_shell_ping(self, host: str, count: int) -> Dict:
        try:
            result = adb_shell(
                self.device_id,
                ["ping", "-c", str(count), "-W", "2", host],
                timeout=max(20, count * 4),
            )
            output = (result.stdout or "").replace("\r", "").strip()
            samples = self._parse_ping_samples(output, host, count)
            if len(samples) < count:
                raise RuntimeError(
                    self._build_ping_failure_message(output, host, count)
                )

            latencies_ms = [
                sample["latency_ms"]
                for sample in samples
                if sample["latency_ms"] is not None
            ]
            stats = None
            if latencies_ms:
                stats = {
                    "min_ms": min(latencies_ms),
                    "avg_ms": round(sum(latencies_ms) / len(latencies_ms), 2),
                    "max_ms": max(latencies_ms),
                }

            return {
                "success": True,
                "mode": "adb_shell_ping",
                "command": f"adb shell ping -c {count} -W 2 {host}",
                "host": host,
                "count": count,
                "samples": samples,
                "latencies_ms": latencies_ms,
                "reachable": bool(latencies_ms),
                "success_count": sum(1 for sample in samples if sample["status"] == "ok"),
                "timeout_count": sum(1 for sample in samples if sample["status"] == "timeout"),
                "passed": sum(1 for sample in samples if sample["status"] == "ok") == count,
                "stats": stats,
                "raw_output": output,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "host": host,
                "count": count,
            }
