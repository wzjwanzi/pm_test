"""Small iperf output parser shared by phone and traffic server logs."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


INTERVAL_PATTERN = re.compile(
    r"^\[\s*\d+\]\s+([0-9.]+\s*-\s*[0-9.]+\s+sec)\s+(.+?)\s+([0-9.]+)\s+([KMGTP])bits/sec\b(.*)$"
)
LOSS_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)\s*\(([0-9.]+)%\)")
UNIT_TO_MBPS = {
    "K": 0.001,
    "M": 1.0,
    "G": 1000.0,
    "T": 1000000.0,
    "P": 1000000000.0,
}


def parse_iperf_text(result_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in str(result_text or "").splitlines() if line.strip()]
    preview_lines = lines[-12:]
    latest_interval = None
    bandwidth_mbps = None
    rate_line = ""

    for line in reversed(lines):
        match = INTERVAL_PATTERN.match(line)
        if not match:
            continue
        bandwidth_value = float(match.group(3))
        unit = match.group(4)
        bandwidth_mbps = round(bandwidth_value * UNIT_TO_MBPS.get(unit, 1.0), 3)
        bandwidth_text = f"{match.group(3)} {unit}bits/sec"
        extra_text = match.group(5).strip()
        loss_match = LOSS_PATTERN.search(extra_text)
        latest_interval = {
            "interval": match.group(1),
            "transfer": match.group(2),
            "bandwidth": bandwidth_text,
            "bandwidth_mbps": bandwidth_mbps,
            "extra": extra_text,
            "line": line,
        }
        if loss_match:
            latest_interval["lost_datagrams"] = int(loss_match.group(1))
            latest_interval["total_datagrams"] = int(loss_match.group(2))
            latest_interval["loss_percent"] = float(loss_match.group(3))
        rate_line = line
        break

    parsed = {
        "line_count": len(lines),
        "preview_lines": preview_lines,
        "result_preview": "\n".join(preview_lines),
        "latest_interval": latest_interval,
    }
    if bandwidth_mbps is not None:
        parsed["bandwidth_mbps"] = bandwidth_mbps
        parsed["rate_line"] = rate_line
    if latest_interval and "loss_percent" in latest_interval:
        parsed["loss_percent"] = latest_interval["loss_percent"]
    return parsed


def parse_iperf_log_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    return parse_iperf_text(text)
