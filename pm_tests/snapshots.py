"""Snapshot collection helpers for PM tests."""

from __future__ import annotations

from network.fiveg_tester import FiveGTester
from network.network_monitor import NetworkMonitor

from .models import NetworkSnapshot, utc_now_iso


class SnapshotCollector:
    """Collect lightweight radio/network snapshots around a case."""

    def collect(self, device_id: str) -> NetworkSnapshot:
        snapshot = NetworkSnapshot(captured_at=utc_now_iso())

        fiveg = FiveGTester(device_id)
        monitor = NetworkMonitor(device_id)

        try:
            snapshot.network_type = fiveg.get_network_type()
        except Exception as exc:  # pragma: no cover - defensive
            snapshot.errors.append(f"network_type: {exc}")

        try:
            snapshot.signal = fiveg.get_signal_strength()
        except Exception as exc:  # pragma: no cover - defensive
            snapshot.errors.append(f"signal: {exc}")

        try:
            snapshot.cell_info = monitor.get_cell_info()
        except Exception as exc:  # pragma: no cover - defensive
            snapshot.errors.append(f"cell_info: {exc}")

        try:
            snapshot.network_info = monitor.get_network_info()
        except Exception as exc:  # pragma: no cover - defensive
            snapshot.errors.append(f"network_info: {exc}")

        return snapshot
