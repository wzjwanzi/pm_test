"""Ping execution helpers for PM tests."""

from __future__ import annotations

import re

from utils.adb_utils import adb_shell

from .models import PingCaseSpec, PingResult, utc_now_iso


class DevicePingExecutor:
    """Run ping on the device via adb shell."""

    latency_pattern = re.compile(r"time[=<]([0-9.]+)\s*ms", re.IGNORECASE)
    packet_loss_pattern = re.compile(r"(\d+(?:\.\d+)?)%\s*packet loss", re.IGNORECASE)
    rtt_pattern = re.compile(
        r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+)",
        re.IGNORECASE,
    )

    def run(self, device_id: str, case: PingCaseSpec) -> PingResult:
        started_at = utc_now_iso()
        count = case.normalized_count()
        timeout = max(case.timeout_seconds, count * 3)

        try:
            result = adb_shell(
                device_id,
                ["ping", "-c", str(count), "-W", "2", case.host],
                timeout=timeout,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            success_count = 0
            latencies: list[float] = []
            packet_loss = None
            stats: dict[str, float] = {}

            for line in lines:
                latency_match = self.latency_pattern.search(line)
                if latency_match:
                    success_count += 1
                    latencies.append(float(latency_match.group(1)))
                    continue

                packet_loss_match = self.packet_loss_pattern.search(line)
                if packet_loss_match:
                    packet_loss = float(packet_loss_match.group(1))
                    continue

                rtt_match = self.rtt_pattern.search(line)
                if rtt_match:
                    stats = {
                        "min_ms": float(rtt_match.group(1)),
                        "avg_ms": float(rtt_match.group(2)),
                        "max_ms": float(rtt_match.group(3)),
                        "mdev_ms": float(rtt_match.group(4)),
                    }

            if not stats and latencies:
                stats = {
                    "min_ms": min(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies), 2),
                    "max_ms": max(latencies),
                }

            ping_status = "completed" if result.returncode == 0 or success_count > 0 else "failed"
            return PingResult(
                status=ping_status,
                host=case.host,
                count=count,
                started_at=started_at,
                ended_at=utc_now_iso(),
                success_count=success_count,
                timeout_count=max(count - success_count, 0),
                packet_loss_percent=packet_loss,
                return_code=result.returncode,
                stats=stats,
                lines=lines,
                raw_output=result.stdout.strip(),
            )
        except Exception as exc:
            return PingResult(
                status="error",
                host=case.host,
                count=count,
                started_at=started_at,
                ended_at=utc_now_iso(),
                success_count=0,
                timeout_count=count,
                packet_loss_percent=100.0,
                return_code=None,
                lines=[],
                raw_output="",
                error=str(exc),
            )
