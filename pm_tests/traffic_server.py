"""SSH helpers for running traffic server commands."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config
from app_settings import get_traffic_settings
from network.iperf_parser import parse_iperf_log_file


@dataclass
class TrafficServerSession:
    """A running traffic server command session."""

    action: str
    command: str
    client: Any
    channel: Any
    stdout_thread: threading.Thread
    stderr_thread: threading.Thread
    local_path: str
    started_at: str


class TrafficServerClient:
    """Run configured traffic commands on the packet injection server."""

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or get_traffic_settings()

    def start_command(self, action: str, command: str, run_id: str, case_name: str) -> TrafficServerSession:
        """Start a remote command and stream stdout/stderr to a local log file."""
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("缺少 paramiko，无法通过 SSH 执行灌包服务器命令。请先安装 requirements.txt。") from exc

        command = str(command or "").strip()
        if not command:
            raise RuntimeError("缺少灌包服务器执行命令。")

        host = str(self.settings.get("server_host") or "").strip()
        if not host:
            raise RuntimeError("缺少灌包服务器地址。")

        output_dir = Path(self.settings.get("server_log_dir") or config.PM_ARTIFACTS_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_case_name = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in case_name)[:80]
        safe_action = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in action)[:60]
        local_path = output_dir / f"{run_id}_{safe_case_name}_{safe_action}.log"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout = int(self.settings.get("server_connect_timeout") or 20)
        client.connect(
            hostname=host,
            port=int(self.settings.get("server_port") or 22),
            username=str(self.settings.get("server_username") or ""),
            password=str(self.settings.get("server_password") or ""),
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )

        transport = client.get_transport()
        if not transport:
            client.close()
            raise RuntimeError("灌包服务器 SSH 连接未建立。")

        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(command)

        lock = threading.Lock()
        fh = local_path.open("a", encoding="utf-8", errors="replace")
        fh.write(
            f"=== started_at={time.strftime('%Y-%m-%dT%H:%M:%S')} "
            f"host={host} action={action} ===\n"
        )
        fh.write(f"$ {command}\n")
        fh.flush()

        def pump(stream_name: str, prefix: str) -> None:
            try:
                while not channel.closed:
                    if stream_name == "stderr":
                        ready = channel.recv_stderr_ready()
                        data = channel.recv_stderr(4096) if ready else b""
                    else:
                        ready = channel.recv_ready()
                        data = channel.recv(4096) if ready else b""
                    if not data:
                        if channel.exit_status_ready():
                            break
                        time.sleep(0.1)
                        continue
                    text = data.decode("utf-8", errors="replace")
                    with lock:
                        fh.write(prefix + text)
                        fh.flush()
            except Exception as exc:
                with lock:
                    fh.write(f"\n[{prefix or 'stdout'} reader error] {exc}\n")
                    fh.flush()

        stdout_thread = threading.Thread(target=pump, args=("stdout", ""), daemon=True)
        stderr_thread = threading.Thread(target=pump, args=("stderr", "[stderr] "), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        session = TrafficServerSession(
            action=action,
            command=command,
            client=client,
            channel=channel,
            stdout_thread=stdout_thread,
            stderr_thread=stderr_thread,
            local_path=str(local_path),
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        session._file_handle = fh  # type: ignore[attr-defined]
        return session

    def stop_command(self, session: TrafficServerSession) -> dict[str, Any]:
        """Stop a remote command session and return its local log metadata."""
        if not session:
            raise RuntimeError("缺少灌包服务器命令会话。")

        exit_status: int | None = None
        try:
            if session.channel and session.channel.exit_status_ready():
                exit_status = session.channel.recv_exit_status()
            if session.channel and not session.channel.closed:
                session.channel.close()
        finally:
            try:
                session.client.close()
            except Exception:
                pass

        session.stdout_thread.join(timeout=3)
        session.stderr_thread.join(timeout=3)
        fh = getattr(session, "_file_handle", None)
        if fh:
            fh.write(f"\n=== stopped_at={time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
            fh.close()

        local_file = Path(session.local_path)
        size_bytes = local_file.stat().st_size if local_file.exists() else 0
        parsed_output = parse_iperf_log_file(local_file) if local_file.exists() else {}
        return {
            "success": size_bytes > 0,
            "action": session.action,
            "command": session.command,
            "exit_status": exit_status,
            "local_path": session.local_path,
            "file_size_bytes": size_bytes,
            "started_at": session.started_at,
            "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **parsed_output,
        }
