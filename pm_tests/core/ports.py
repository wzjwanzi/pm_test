"""Adapter port contracts for PM execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from pm_tests.core.models import AdapterError, Artifact, StepPlan


@dataclass(slots=True)
class AdapterResult:
    """Normalized result returned by concrete adapters."""

    success: bool
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    error: AdapterError | None = None


class StepPort(Protocol):
    """Adapter protocol used by StepRunner."""

    def run_step(self, step: StepPlan) -> AdapterResult:
        """Run one step and return a normalized result."""
