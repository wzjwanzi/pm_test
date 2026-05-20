"""Packet capture helpers for PM test runs."""
from __future__ import annotations

import shlex
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

import config
from utils.adb_utils import adb_shell_script, adb_shell_text, command_exists, run_adb


@dataclass
class CaptureSession:
    """A running device-side packet capture session."""

    session_id: str
    device_id: str
    binary: str
    interface: str
    local_path: str
    remote_path: str
    remote_pid_path: str
    pid: str | None
    host_filter: str | None
    started_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class PacketCaptureService:
    """Start and stop device-side packet captures."""

    def __init__(self, artifacts_root: str | Path | None = None):
        self.artifacts_root = Path(artifacts_root or config.PM_ARTIFACTS_DIR)

    def inspect_support(self, device_id: str) -> dict:
        """Return the current packet capture capability for a device."""
        if not device_id:
            return {
                "supported": False,
                "error": "缺少设备 ID。",
                "hint": self._missing_binary_hint(),
            }

        try:
            binary = self._detect_capture_binary(device_id)
            return {
                "supported": True,
                "binary": binary,
                "interface": config.PACKET_CAPTURE_INTERFACE,
                "device_dir": config.PACKET_CAPTURE_DEVICE_DIR,
            }
        except Exception as exc:
            return {
                "supported": False,
                "error": str(exc),
                "hint": self._missing_binary_hint(),
                "interface": config.PACKET_CAPTURE_INTERFACE,
                "device_dir": config.PACKET_CAPTURE_DEVICE_DIR,
            }

    def start(
        self,
        device_id: str,
        run_id: str,
        case_name: str,
        host_filter: str | None = None,
    ) -> CaptureSession:
        """Start a device-side tcpdump capture and return the session."""
        support = self.inspect_support(device_id)
        if not support.get("supported"):
            raise RuntimeError(support.get("error") or "当前设备不支持抓包。")

        capture_dir = self.artifacts_root / run_id / "captures"
        capture_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        slug = self._slugify(case_name)
        filename = f"{timestamp}_{slug}_{uuid4().hex[:8]}.pcap"
        local_path = capture_dir / filename
        remote_path = f"{config.PACKET_CAPTURE_DEVICE_DIR.rstrip('/')}/{filename}"
        remote_pid_path = f"{remote_path}.pid"

        tcpdump_args = [
            support["binary"],
            "-i",
            config.PACKET_CAPTURE_INTERFACE,
            "-s",
            "0",
            "-U",
            "-w",
            remote_path,
        ]
        if host_filter:
            tcpdump_args.extend(["host", host_filter])

        tcpdump_command = shlex.join(tcpdump_args)
        script = " && ".join(
            [
                f"mkdir -p {shlex.quote(config.PACKET_CAPTURE_DEVICE_DIR)}",
                f"rm -f {shlex.quote(remote_path)} {shlex.quote(remote_pid_path)}",
                f"({tcpdump_command} >/dev/null 2>&1 & echo $! > {shlex.quote(remote_pid_path)})",
            ]
        )
        adb_shell_script(device_id, script, check=True, timeout=20)
        time.sleep(config.PACKET_CAPTURE_START_WAIT_SECONDS)

        pid = self._read_pid(device_id, remote_pid_path)
        if not pid:
            raise RuntimeError("抓包进程未成功启动，请检查 tcpdump 权限。")

        return CaptureSession(
            session_id=f"cap-{uuid4().hex[:12]}",
            device_id=device_id,
            binary=support["binary"],
            interface=config.PACKET_CAPTURE_INTERFACE,
            local_path=str(local_path),
            remote_path=remote_path,
            remote_pid_path=remote_pid_path,
            pid=pid,
            host_filter=host_filter,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def stop(self, session: CaptureSession) -> dict:
        """Stop a running capture session and pull the pcap to the host."""
        if not session:
            raise RuntimeError("缺少抓包会话。")

        pid = self._read_pid(session.device_id, session.remote_pid_path, required=False) or session.pid
        if pid:
            adb_shell_script(
                session.device_id,
                f"kill {shlex.quote(pid)} 2>/dev/null || true",
                timeout=15,
            )
        time.sleep(config.PACKET_CAPTURE_STOP_WAIT_SECONDS)

        pull_result = run_adb(
            ["pull", session.remote_path, session.local_path],
            device_id=session.device_id,
            timeout=60,
        )
        cleanup_script = " && ".join(
            [
                f"rm -f {shlex.quote(session.remote_pid_path)}",
                f"rm -f {shlex.quote(session.remote_path)}",
            ]
        )
        adb_shell_script(session.device_id, cleanup_script, timeout=15)

        local_file = Path(session.local_path)
        if pull_result.returncode != 0:
            error = pull_result.stderr.strip() or pull_result.stdout.strip() or "拉取 pcap 失败。"
            return {
                "success": False,
                "error": error,
                "session": session.to_dict(),
                "local_path": session.local_path,
            }

        if not local_file.exists():
            return {
                "success": False,
                "error": "pcap 文件未生成到本地。",
                "session": session.to_dict(),
                "local_path": session.local_path,
            }

        file_size = local_file.stat().st_size
        return {
            "success": file_size > 0,
            "file_size_bytes": file_size,
            "local_path": str(local_file),
            "filename": local_file.name,
            "session": session.to_dict(),
            "message": "抓包完成并已拉回本地。" if file_size > 0 else "pcap 文件为空。",
        }

    def _detect_capture_binary(self, device_id: str) -> str:
        for candidate in config.PACKET_CAPTURE_BINARY_CANDIDATES:
            if "/" not in candidate:
                if command_exists(device_id, candidate):
                    return candidate
                continue

            script = f"if [ -x {shlex.quote(candidate)} ]; then echo {shlex.quote(candidate)}; fi"
            resolved = adb_shell_text(device_id, ["sh", "-c", script], timeout=10)
            if resolved.strip():
                return candidate

        raise RuntimeError("设备上未检测到可执行 tcpdump。")

    def _read_pid(self, device_id: str, remote_pid_path: str, required: bool = True) -> str | None:
        result = adb_shell_text(
            device_id,
            ["sh", "-c", f"cat {shlex.quote(remote_pid_path)} 2>/dev/null || true"],
            timeout=10,
        ).strip()
        if result or not required:
            return result or None
        raise RuntimeError("抓包进程 PID 未写入设备。")

    def _missing_binary_hint(self) -> str:
        candidates = ", ".join(config.PACKET_CAPTURE_BINARY_CANDIDATES)
        return (
            "请先在手机上准备 tcpdump，常见方式是将可执行文件推送到 "
            f"`/data/local/tmp/tcpdump` 并赋予 755 权限。当前检测路径: {candidates}"
        )

    def _slugify(self, value: str) -> str:
        compact = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
        compact = compact.strip("_")
        return compact[:48] or "case"
