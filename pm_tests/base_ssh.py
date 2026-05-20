"""Helpers for collecting basestation SSH command output."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import config
from app_settings import get_ssh_settings


@dataclass
class BaseSshLogSession:
    """A running SSH log collection session."""

    client: Any
    channel: Any
    stdout_thread: threading.Thread
    stderr_thread: threading.Thread
    local_path: str
    started_at: str
    command: str = ""


class BaseSshClient:
    """Small wrapper around Paramiko for basestation SSH log collection."""

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or get_ssh_settings()

    def start_output_log(self, run_id: str, case_name: str) -> BaseSshLogSession:
        """Start the configured long-running SSH log command and stream output to disk."""
        command = str(self.settings.get("log_command") or "").strip()
        if not command:
            raise RuntimeError("Missing base SSH log command.")
        return self.start_command(command, run_id, case_name, "base_ssh")

    def start_command(
        self,
        command: str,
        run_id: str,
        case_name: str,
        label: str = "",
    ) -> BaseSshLogSession:
        """Start a long-running SSH command and stream output to a named log file."""
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("缺少 paramiko，无法执行基站 SSH 输出日志。请先安装 requirements.txt。") from exc

        host = str(self.settings.get("host") or "").strip()
        if not host:
            raise RuntimeError("缺少基站 SSH 主机。")
        command = str(command or "").strip()
        if not command:
            raise RuntimeError("Missing base SSH command.")

        output_dir = Path(
            self.settings.get("log_output_dir")
            or self.settings.get("log_download_dir")
            or config.PM_ARTIFACTS_DIR
        )
        safe_case_name = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in case_name)[:80]
        safe_label = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (label or "base_ssh"))[:80]
        file_name = f"{run_id}_{safe_case_name}_{safe_label}.log"

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=int(self.settings.get("port") or 22),
            username=str(self.settings.get("username") or ""),
            password=str(self.settings.get("password") or ""),
            timeout=int(self.settings.get("connect_timeout") or 20),
            banner_timeout=int(self.settings.get("connect_timeout") or 20),
            auth_timeout=int(self.settings.get("connect_timeout") or 20),
            look_for_keys=False,
            allow_agent=False,
        )

        transport = client.get_transport()
        if not transport:
            client.close()
            raise RuntimeError("基站 SSH 连接未建立。")

        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(command)

        lock = threading.Lock()
        fh, local_path, fallback_from = _open_log_file(output_dir, file_name)
        fh.write(f"=== started_at={time.strftime('%Y-%m-%dT%H:%M:%S')} host={host} ===\n")
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

        session = BaseSshLogSession(
            client=client,
            channel=channel,
            stdout_thread=stdout_thread,
            stderr_thread=stderr_thread,
            local_path=str(local_path),
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            command=command,
        )
        session._file_handle = fh  # type: ignore[attr-defined]
        session._fallback_from = fallback_from  # type: ignore[attr-defined]
        return session

    def run_command(self, command: str) -> dict[str, Any]:
        """Run one SSH command and return stdout, stderr, and exit status."""
        try:
            import paramiko
        except ImportError as exc:
            raise RuntimeError("Missing paramiko; cannot run base SSH command.") from exc

        host = str(self.settings.get("host") or "").strip()
        if not host:
            raise RuntimeError("Missing base SSH host.")
        command = str(command or "").strip()
        if not command:
            raise RuntimeError("Missing base SSH command.")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=host,
                port=int(self.settings.get("port") or 22),
                username=str(self.settings.get("username") or ""),
                password=str(self.settings.get("password") or ""),
                timeout=int(self.settings.get("connect_timeout") or 20),
                banner_timeout=int(self.settings.get("connect_timeout") or 20),
                auth_timeout=int(self.settings.get("connect_timeout") or 20),
                look_for_keys=False,
                allow_agent=False,
            )
            _stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")
            return {
                "success": exit_status == 0,
                "command": command,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_status": exit_status,
            }
        finally:
            client.close()

    def stop_output_log(self, session: BaseSshLogSession) -> dict[str, Any]:
        """Stop a running SSH log command and close the output file."""
        if not session:
            raise RuntimeError("缺少基站 SSH 输出日志会话。")

        try:
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
        result = {
            "success": size_bytes > 0,
            "local_path": session.local_path,
            "file_size_bytes": size_bytes,
            "started_at": session.started_at,
            "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        fallback_from = getattr(session, "_fallback_from", "")
        if fallback_from:
            result["log_dir_fallback_from"] = fallback_from
        return result


def _open_log_file(output_dir: Path, file_name: str):
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        local_path = output_dir / file_name
        return local_path.open("a", encoding="utf-8", errors="replace"), local_path, ""
    except PermissionError:
        fallback_dir = Path(config.PM_ARTIFACTS_DIR)
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / file_name
        return fallback_path.open("a", encoding="utf-8", errors="replace"), fallback_path, str(output_dir)
