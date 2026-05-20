"""ADB helpers with Windows-friendly path resolution."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence


class ADBError(RuntimeError):
    """Raised when an ADB command cannot be executed successfully."""


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.append(exe_dir)
        roots.append(exe_dir / "_internal")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass).resolve())

    roots.append(Path(__file__).resolve().parents[1])
    roots.append(Path.cwd())

    deduped: list[Path] = []
    for root in roots:
        if root not in deduped:
            deduped.append(root)
    return deduped


def get_adb_path() -> str:
    env_path = os.getenv("ADB_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    path_adb = shutil.which("adb")
    if path_adb:
        return path_adb

    executable_name = "adb.exe" if os.name == "nt" else "adb"
    for root in _candidate_roots():
        for candidate in (
            root / executable_name,
            root / "scrcpy-win64-v2.0" / executable_name,
            root / "tools" / executable_name,
        ):
            if candidate.exists():
                return str(candidate)

    raise ADBError(
        "未找到 adb。请安装 Android Platform Tools，或将项目自带的 adb.exe 保留在 "
        "scrcpy-win64-v2.0 目录中。"
    )


def _stringify(parts: Iterable[object]) -> list[str]:
    return [str(part) for part in parts]


def run_adb(
    args: Sequence[object],
    *,
    device_id: str | None = None,
    check: bool = False,
    timeout: int | None = 30,
) -> subprocess.CompletedProcess[str]:
    command = [get_adb_path()]
    if device_id:
        command.extend(["-s", device_id])
    command.extend(_stringify(args))

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        creationflags=creationflags,
    )

    if check and result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip() or "未知 ADB 错误"
        raise ADBError(output)

    return result


def adb_shell(
    device_id: str,
    shell_args: Sequence[object],
    *,
    check: bool = False,
    timeout: int | None = 30,
) -> subprocess.CompletedProcess[str]:
    return run_adb(["shell", *_stringify(shell_args)], device_id=device_id, check=check, timeout=timeout)


def adb_shell_text(
    device_id: str,
    shell_args: Sequence[object],
    *,
    check: bool = False,
    timeout: int | None = 30,
) -> str:
    return adb_shell(device_id, shell_args, check=check, timeout=timeout).stdout.strip()


def adb_shell_script(
    device_id: str,
    script: str,
    *,
    check: bool = False,
    timeout: int | None = 30,
) -> subprocess.CompletedProcess[str]:
    return adb_shell(device_id, ["sh", "-c", script], check=check, timeout=timeout)


def command_exists(device_id: str, command_name: str) -> bool:
    result = adb_shell(device_id, ["which", command_name], timeout=10)
    return result.returncode == 0 and bool(result.stdout.strip())


def get_connected_devices() -> list[str]:
    result = run_adb(["devices"], check=True, timeout=15)
    devices: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        if "\tdevice" in line:
            devices.append(line.split("\t", 1)[0].strip())
    return devices
