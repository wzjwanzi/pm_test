"""Saved desktop case models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(slots=True)
class CaseStep:
    step_id: str
    action: str
    label: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)
    required: bool = True

    @classmethod
    def new(
        cls,
        action: str,
        label: str,
        params: dict[str, Any],
        *,
        enabled: bool = True,
        required: bool = True,
    ) -> "CaseStep":
        return cls(
            step_id=f"step_{uuid4().hex[:8]}",
            action=action,
            label=label,
            enabled=enabled,
            params=dict(params),
            required=required,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseStep":
        return cls(
            step_id=str(data.get("step_id") or f"step_{uuid4().hex[:8]}"),
            action=str(data.get("action") or ""),
            label=str(data.get("label") or data.get("action") or "step"),
            enabled=bool(data.get("enabled", True)),
            params=dict(data.get("params") or {}),
            required=bool(data.get("required", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "label": self.label,
            "enabled": self.enabled,
            "required": self.required,
            "params": dict(self.params),
        }


@dataclass(slots=True)
class SavedCase:
    schema_version: int
    case_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    steps: list[CaseStep] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        name: str,
        steps: list[CaseStep],
        description: str = "",
    ) -> "SavedCase":
        stamp = now_iso()
        return cls(
            schema_version=SCHEMA_VERSION,
            case_id=f"case_{uuid4().hex[:8]}",
            name=name,
            description=description,
            created_at=stamp,
            updated_at=stamp,
            steps=list(steps),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedCase":
        return cls(
            schema_version=int(data.get("schema_version") or SCHEMA_VERSION),
            case_id=str(data.get("case_id") or f"case_{uuid4().hex[:8]}"),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
            steps=[CaseStep.from_dict(item) for item in data.get("steps") or []],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.to_dict() for step in self.steps],
        }


def validate_case(case: SavedCase) -> ValidationResult:
    result = ValidationResult()
    if not case.name.strip():
        result.errors.append("用例名称不能为空")
    if not any(step.enabled for step in case.steps):
        result.errors.append("至少需要一个启用步骤")

    has_start = any(step.enabled and step.action.endswith("_start") for step in case.steps)
    has_stop = any(step.enabled and step.action.endswith("_stop") for step in case.steps)
    if has_start and not has_stop:
        result.warnings.append("存在开始步骤但没有停止步骤，执行结束会尝试清理")

    return result
