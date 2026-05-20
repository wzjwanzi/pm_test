"""Shared helpers for Android network diagnostics."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

from utils.adb_utils import adb_shell_script, adb_shell_text


EXCLUDED_INTERFACE_PREFIXES = (
    "lo",
    "dummy",
    "tunl",
    "gre",
    "gretap",
    "erspan",
    "sit",
    "ip_vti",
    "ip6tnl",
    "ip6gre",
    "ip6_vti",
)

PREFERRED_INTERFACE_PREFIXES = ("rmnet", "ccmni", "wlan", "swlan", "rndis")


@dataclass
class InterfaceStats:
    name: str
    rx_bytes: int
    tx_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.rx_bytes + self.tx_bytes


def parse_proc_net_dev(proc_net_dev_text: str) -> list[InterfaceStats]:
    interfaces: list[InterfaceStats] = []
    for raw_line in proc_net_dev_text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line or line.startswith("Inter-") or line.startswith("face |"):
            continue

        name, stats = line.split(":", 1)
        parts = stats.split()
        if len(parts) < 16:
            continue

        interfaces.append(
            InterfaceStats(
                name=name.strip(),
                rx_bytes=int(parts[0]),
                tx_bytes=int(parts[8]),
            )
        )
    return interfaces


def get_interface_stats(device_id: str) -> list[InterfaceStats]:
    output = adb_shell_text(device_id, ["cat", "/proc/net/dev"], check=True, timeout=15)
    return parse_proc_net_dev(output)


def _priority(interface_name: str) -> int:
    for index, prefix in enumerate(PREFERRED_INTERFACE_PREFIXES):
        if interface_name.startswith(prefix):
            return index
    return len(PREFERRED_INTERFACE_PREFIXES)


def pick_active_interface(interfaces: Iterable[InterfaceStats]) -> InterfaceStats | None:
    candidates = [
        interface
        for interface in interfaces
        if not interface.name.startswith(EXCLUDED_INTERFACE_PREFIXES)
    ]
    if not candidates:
        return None

    non_zero = [interface for interface in candidates if interface.total_bytes > 0]
    ranked = non_zero or candidates
    ranked.sort(key=lambda item: (_priority(item.name), -item.total_bytes, item.name))
    return ranked[0]


def get_active_interface(device_id: str) -> InterfaceStats:
    active = pick_active_interface(get_interface_stats(device_id))
    if not active:
        raise RuntimeError("未能识别设备上的活跃网络接口。")
    return active


def get_interface_ip_info(device_id: str, interface_name: str) -> str:
    return adb_shell_text(device_id, ["ip", "addr", "show", interface_name], timeout=15)


def get_connectivity_dump(device_id: str) -> str:
    return adb_shell_text(device_id, ["dumpsys", "connectivity"], check=True, timeout=20)


def parse_bandwidth_from_connectivity(connectivity_dump: str, interface_name: str | None = None) -> dict | None:
    interface_pattern = re.escape(interface_name) if interface_name else r"[A-Za-z0-9_.-]+"
    pattern = re.compile(
        rf"InterfaceName:\s*{interface_pattern}.*?LinkUpBandwidth>=([0-9]+)Kbps\s+LinkDnBandwidth>=([0-9]+)Kbps",
        re.DOTALL,
    )
    match = pattern.search(connectivity_dump)
    if not match:
        return None

    up_kbps = int(match.group(1))
    down_kbps = int(match.group(2))
    return {
        "up_mbps": round(up_kbps / 1000, 2),
        "down_mbps": round(down_kbps / 1000, 2),
    }


def build_http_download_script(url: str, duration: int, repeat: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "http":
        raise ValueError("当前设备缺少 curl/wget，仅支持使用 nc 对 http 链接做下载测试。")
    if not parsed.hostname:
        raise ValueError("无效的下载 URL。")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    port = parsed.port or 80
    request = (
        f"GET {path} HTTP/1.1\\r\\n"
        f"Host: {parsed.hostname}\\r\\n"
        "Connection: close\\r\\n"
        "\\r\\n"
    )

    request_script = (
        f"printf '%b' {shlex.quote(request)} | "
        f"nc {shlex.quote(parsed.hostname)} {port} >/dev/null"
    )
    if repeat:
        return f"while true; do {request_script} || exit $?; done"
    return request_script


def run_download_probe(device_id: str, url: str, duration: int, repeat: bool = False) -> None:
    script = build_http_download_script(url, duration, repeat=repeat)
    adb_shell_script(device_id, script, check=True, timeout=duration + 15)
