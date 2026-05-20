"""State objects for the desktop UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_status(run: dict[str, Any] | None) -> str:
    """Return the stable run status value for display."""

    if not run:
        return "queued"
    return str(run.get("status") or run.get("state") or "queued")


@dataclass(slots=True)
class CaseDraft:
    """Editable desktop representation of one PM case."""

    name: str
    host: str
    count: int = 5
    capture_enabled: bool = False
    ping_enabled: bool = True
    server_action: str = "none"
    group: str = ""
    label: str = ""

    def to_legacy_case(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "host": self.host,
            "count": self.count,
            "capture_enabled": self.capture_enabled,
            "ping_enabled": self.ping_enabled,
            "server_action": self.server_action or "none",
        }


@dataclass(slots=True)
class DesktopState:
    """Shared state for desktop widgets."""

    selected_device_id: str = ""
    selected_run_id: str = ""
    selected_case_index: int = -1
    case_queue: list[CaseDraft] = field(default_factory=list)
    latest_run: dict[str, Any] | None = None
    message: str = ""

    def add_case(self, case: CaseDraft) -> None:
        self.case_queue.append(case)
        self.selected_case_index = len(self.case_queue) - 1

    def select_case(self, index: int) -> None:
        if 0 <= index < len(self.case_queue):
            self.selected_case_index = index

    def selected_case(self) -> CaseDraft | None:
        if 0 <= self.selected_case_index < len(self.case_queue):
            return self.case_queue[self.selected_case_index]
        return None

    def clear_cases(self) -> None:
        self.case_queue.clear()
        self.selected_case_index = -1
