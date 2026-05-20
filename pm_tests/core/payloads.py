"""Utilities for keeping run JSON compact while preserving full payloads."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pm_tests.core.models import Artifact, StepRecord


DEFAULT_PAYLOAD_THRESHOLD = 4096


def externalize_large_step_payloads(
    step_record: StepRecord,
    case_dir: str | Path,
    *,
    threshold: int = DEFAULT_PAYLOAD_THRESHOLD,
) -> StepRecord:
    """Write oversized strings in step data to artifact files."""

    base_dir = Path(case_dir)
    step_dir = base_dir / "payloads" / _safe_name(step_record.step_id)
    step_record.data = _externalize_value(
        step_record.data,
        step_record=step_record,
        step_dir=step_dir,
        threshold=threshold,
        path_parts=[],
    )
    return step_record


def _externalize_value(
    value: Any,
    *,
    step_record: StepRecord,
    step_dir: Path,
    threshold: int,
    path_parts: list[str],
) -> Any:
    if isinstance(value, str):
        if len(value) <= threshold:
            return value
        return _write_payload(value, step_record=step_record, step_dir=step_dir, path_parts=path_parts)
    if isinstance(value, dict):
        return {
            key: _externalize_value(
                item,
                step_record=step_record,
                step_dir=step_dir,
                threshold=threshold,
                path_parts=[*path_parts, str(key)],
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _externalize_value(
                item,
                step_record=step_record,
                step_dir=step_dir,
                threshold=threshold,
                path_parts=[*path_parts, str(index)],
            )
            for index, item in enumerate(value)
        ]
    return value


def _write_payload(
    value: str,
    *,
    step_record: StepRecord,
    step_dir: Path,
    path_parts: list[str],
) -> dict[str, Any]:
    step_dir.mkdir(parents=True, exist_ok=True)
    label = ".".join(path_parts) if path_parts else "value"
    filename = "-".join(_safe_name(part) for part in (path_parts or ["value"])) + ".txt"
    path = step_dir / filename
    path.write_text(value, encoding="utf-8")
    relative_path = path.relative_to(step_dir.parents[1]).as_posix()
    byte_count = len(value.encode("utf-8"))
    reference = {
        "type": "external_payload",
        "path": relative_path,
        "bytes": byte_count,
        "characters": len(value),
        "preview": _preview(value),
    }
    step_record.artifacts.append(
        Artifact(
            kind="external_payload",
            path=relative_path,
            label=label,
            metadata={
                "bytes": byte_count,
                "characters": len(value),
                "source": label,
            },
        )
    )
    return reference


def _preview(value: str, limit: int = 160) -> str:
    compact = value.replace("\r", " ").replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return cleaned or "payload"
