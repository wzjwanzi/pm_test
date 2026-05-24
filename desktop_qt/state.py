from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class QtDesktopState:
    selected_devices: list[str] = field(default_factory=list)
    selected_case: Any | None = None
    selected_run_id: str = ""
    selected_run_ids: list[str] = field(default_factory=list)
    latest_run: dict[str, Any] | None = None
    run_mode: str = "single"
    preflight: dict[str, Any] = field(default_factory=dict)
