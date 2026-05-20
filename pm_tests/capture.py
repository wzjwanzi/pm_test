"""Packet capture abstractions for PM tests."""

from __future__ import annotations

import shlex
import time
from pathlib import Path
from typing import Protocol

from utils.adb_utils import adb_shell_script, run_adb

from .models import CaptureRecord, utc_now_iso


class CaptureSession(Protocol):
    """Capture lifecycle interface."""

    def stop(self) -> CaptureRecord:
        """Stop capture and return the final record."""


class CaptureBackend(Protocol):
    """Factory for per-case capture sessions."""

    def start(self, device_id: str, artifact_dir: Path, host: str | None = None) -> CaptureSession:
        """Start capture for a case."""


class DeviceTcpdumpCaptureBackend:
    """Best-effort tcpdump capture on device side."""

    backend_name = "device_tcpdump"

    def start(self, device_id: str, artifact_dir: Path, host: str | None = None) -> CaptureSession:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        session = _DeviceTcpdumpSession(device_id, artifact_dir, host=host, backend=self.backend_name)
        session.start()
        return session


class _NoopCaptureSession:
    def __init__(self, record: CaptureRecord):
        self._record = record

    def stop(self) -> CaptureRecord:
        if not self._record.stopped_at:
            self._record.stopped_at = utc_now_iso()
        return self._record


class _DeviceTcpdumpSession:
    def __init__(self, device_id: str, artifact_dir: Path, *, host: str | None, backend: str):
        self.device_id = device_id
        self.artifact_dir = artifact_dir
        self.host = host
        self.backend = backend
        stem = artifact_dir.name
        self.remote_pcap = f"/sdcard/{stem}.pcap"
        self.remote_log = f"/sdcard/{stem}.tcpdump.log"
        self.remote_pid = f"/sdcard/{stem}.tcpdump.pid"
        self.local_pcap = artifact_dir / "capture.pcap"
        self.local_log = artifact_dir / "capture.log"
        self.record = CaptureRecord(
            backend=self.backend,
            status="starting",
            started_at=utc_now_iso(),
            remote_pcap_path=self.remote_pcap,
            local_pcap_path=str(self.local_pcap),
            local_log_path=str(self.local_log),
        )
        self._privilege = "shell"

    def start(self) -> None:
        try:
            if not self._tcpdump_exists():
                self.record.status = "unavailable"
                self.record.error = "tcpdump not found on device."
                return

            filter_expr = "icmp"
            if self.host:
                filter_expr += f" and host {self.host}"

            start_script = (
                f"rm -f {shlex.quote(self.remote_pcap)} {shlex.quote(self.remote_log)} {shlex.quote(self.remote_pid)}; "
                f"tcpdump -i any -s 0 -w {shlex.quote(self.remote_pcap)} {shlex.quote(filter_expr)} "
                f">{shlex.quote(self.remote_log)} 2>&1 & echo $! > {shlex.quote(self.remote_pid)}"
            )
            adb_shell_script(self.device_id, start_script, check=True, timeout=15)
            time.sleep(1.0)

            pid = adb_shell_script(
                self.device_id,
                f"cat {shlex.quote(self.remote_pid)} 2>/dev/null || true",
                timeout=10,
            ).stdout.strip()
            if not pid:
                self.record.status = "failed"
                self.record.error = "tcpdump did not create a pid file."
                return

            self.record.status = "running"
            self.record.privilege = self._privilege
        except Exception as exc:
            self.record.status = "failed"
            self.record.error = str(exc)

    def stop(self) -> CaptureRecord:
        if self.record.status not in {"running", "failed", "unavailable", "starting"}:
            if not self.record.stopped_at:
                self.record.stopped_at = utc_now_iso()
            return self.record

        try:
            pid = adb_shell_script(
                self.device_id,
                f"cat {shlex.quote(self.remote_pid)} 2>/dev/null || true",
                timeout=10,
            ).stdout.strip()
            if pid:
                adb_shell_script(
                    self.device_id,
                    f"kill {shlex.quote(pid)} 2>/dev/null || true",
                    timeout=10,
                )
            time.sleep(1.0)

            self._pull_if_exists(self.remote_log, self.local_log)
            if self._pull_if_exists(self.remote_pcap, self.local_pcap):
                self.record.status = "captured"
            elif self.record.status == "running":
                self.record.status = "no_file"
                self.record.error = "tcpdump stopped but no pcap file was pulled."
        except Exception as exc:
            if self.record.status == "running":
                self.record.status = "failed"
            self.record.error = str(exc)
        finally:
            self.record.stopped_at = utc_now_iso()
        return self.record

    def _tcpdump_exists(self) -> bool:
        result = adb_shell_script(
            self.device_id,
            "command -v tcpdump >/dev/null 2>&1 && echo yes || true",
            timeout=10,
        )
        return "yes" in result.stdout

    def _pull_if_exists(self, remote_path: str, local_path: Path) -> bool:
        exists = adb_shell_script(
            self.device_id,
            f"test -f {shlex.quote(remote_path)} && echo yes || true",
            timeout=10,
        )
        if "yes" not in exists.stdout:
            return False

        local_path.parent.mkdir(parents=True, exist_ok=True)
        run_adb(
            ["pull", remote_path, str(local_path)],
            device_id=self.device_id,
            check=True,
            timeout=60,
        )
        return True


def start_capture_with_fallback(
    backend: CaptureBackend,
    device_id: str,
    artifact_dir: Path,
    host: str | None = None,
) -> CaptureSession:
    """Start capture and always return a session object."""

    try:
        return backend.start(device_id, artifact_dir, host=host)
    except Exception as exc:  # pragma: no cover - defensive
        return _NoopCaptureSession(
            CaptureRecord(
                backend=getattr(backend, "backend_name", "unknown"),
                status="failed",
                started_at=utc_now_iso(),
                stopped_at=utc_now_iso(),
                error=str(exc),
            )
        )
