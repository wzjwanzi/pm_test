"""Helpers for desktop run artifact handoff."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from desktop.formatters import extract_step_rows
from desktop.state import normalize_status


def artifact_dir_for_run(run: dict[str, Any] | None) -> Path:
    """Return the artifact directory for a run or raise a clear error."""

    if not run:
        raise ValueError("No run selected.")
    artifact_dir = run.get("artifact_dir")
    if not artifact_dir:
        raise ValueError("Selected run has no artifact directory.")
    return Path(str(artifact_dir))


def build_run_report(run: dict[str, Any]) -> str:
    """Build a compact Markdown report for a run."""

    summary = run.get("summary") or {}
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    error = summary.get("error", 0)
    skipped = summary.get("skipped", 0)
    lines = [
        f"# Run Report: {run.get('run_id', '-')}",
        "",
        f"- Device: `{run.get('device_id', '-')}`",
        f"- Status: `{normalize_status(run)}`",
        f"- Passed: `{passed}/{total}`",
        f"- Failed: `{failed}`",
        f"- Error: `{error}`",
        f"- Skipped: `{skipped}`",
        f"- Artifacts: `{run.get('artifact_dir', '-')}`",
        "",
        "## Steps",
        "",
        "| Case | Step | Adapter | Status | Message | Error |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    rows = extract_step_rows(run)
    if not rows:
        lines.append("| - | - | - | - | No step records. |  |")
    for row in rows:
        lines.append(
            "| {case} | {step} | {adapter} | {status} | {message} | {error} |".format(
                case=_cell(row["case"]),
                step=_cell(row["step"]),
                adapter=_cell(row["adapter"]),
                status=_cell(row["status"]),
                message=_cell(row["message"]),
                error=_cell(row["error"]),
            )
        )
    payloads = extract_external_payloads(run)
    if payloads:
        lines.extend(
            [
                "",
                "## External Payloads",
                "",
                "| Case | Step | Label | Path | Bytes | Characters |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for payload in payloads:
            lines.append(
                "| {case} | {step} | {label} | {path} | {bytes} | {characters} |".format(
                    case=_cell(payload["case"]),
                    step=_cell(payload["step"]),
                    label=_cell(payload["label"]),
                    path=_cell(payload["path"]),
                    bytes=_cell(payload["bytes"]),
                    characters=_cell(payload["characters"]),
                )
            )
    lines.append("")
    return "\n".join(lines)


def extract_external_payloads(run: dict[str, Any] | None) -> list[dict[str, str]]:
    """Return report rows for external payload artifacts in a run."""

    if not run:
        return []
    rows: list[dict[str, str]] = []
    for case in run.get("case_records") or []:
        case_name = str(case.get("name") or case.get("case_id") or "-")
        for step in case.get("step_records") or []:
            step_id = str(step.get("step_id") or step.get("kind") or "-")
            for artifact in step.get("artifacts") or []:
                if artifact.get("kind") != "external_payload":
                    continue
                metadata = artifact.get("metadata") or {}
                rows.append(
                    {
                        "case": case_name,
                        "step": step_id,
                        "label": str(artifact.get("label") or metadata.get("source") or "-"),
                        "path": str(artifact.get("path") or "-"),
                        "bytes": str(metadata.get("bytes") or ""),
                        "characters": str(metadata.get("characters") or ""),
                    }
                )
    return rows


def export_run_report(run: dict[str, Any], output_dir: str | Path | None = None) -> Path:
    """Write a compact run report to disk."""

    target_dir = Path(output_dir) if output_dir is not None else artifact_dir_for_run(run)
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / "run_report.md"
    report_path.write_text(build_run_report(run), encoding="utf-8")
    return report_path


def open_artifact_dir(
    run: dict[str, Any] | None,
    *,
    opener: Callable[[Path], Any] | None = None,
) -> Path:
    """Open the artifact directory for a run and return the resolved path."""

    artifact_dir = artifact_dir_for_run(run)
    if not artifact_dir.exists():
        raise FileNotFoundError(f"Artifact directory does not exist: {artifact_dir}")
    open_path = artifact_dir.resolve()
    if opener is None:
        opener = _default_opener
    opener(open_path)
    return open_path


def _default_opener(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        raise RuntimeError("Opening artifact directories is only implemented for Windows.")


def _cell(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|").strip()
    if len(text) > 180:
        return text[:177] + "..."
    return text
