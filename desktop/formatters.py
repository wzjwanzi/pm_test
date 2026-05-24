"""Formatting helpers for desktop run displays."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from desktop.state import normalize_status


def format_error(error: dict[str, Any] | str | None) -> str:
    """Return a compact structured error string."""

    if not error:
        return ""
    if isinstance(error, str):
        return error
    code = str(error.get("code") or "")
    adapter = str(error.get("adapter") or "")
    message = str(error.get("message") or "")
    prefix = " ".join(item for item in (code, adapter) if item).strip()
    if prefix and message:
        return f"{prefix}: {message}"
    return prefix or message


def format_run_summary(run: dict[str, Any] | None) -> str:
    """Return a short summary for the selected run."""

    if not run:
        return "No run selected."
    summary = run.get("summary") or {}
    passed = summary.get("passed", 0)
    total = summary.get("total", 0)
    failed = summary.get("failed", 0)
    return (
        f"Run: {run.get('run_id', '-')}\n"
        f"Device: {run.get('device_id', '-')}\n"
        f"Status: {normalize_status(run)}\n"
        f"Passed: {passed}/{total}\n"
        f"Failed: {failed}\n"
        f"Artifacts: {run.get('artifact_dir', '-')}"
    )


def format_run_console(run: dict[str, Any] | None) -> str:
    """Return chronological console text for a selected run."""

    if not run:
        return "No run selected"

    cases = _console_cases(run)
    total_steps = sum(_case_total_steps(case) for case in cases)
    if total_steps == 0:
        return f"{format_run_summary(run)}\n\nNo step records."

    lines: list[str] = []
    current = 0
    for case in cases:
        case_name = str(case.get("name") or case.get("case_id") or "-")
        case_warnings = _case_warnings(case)
        case_warnings_printed = False
        for step in case.get("step_records") or []:
            current += 1
            data = step.get("data") if isinstance(step.get("data"), dict) else {}
            label = _step_label(step, data)
            lines.append(f"[{current}/{total_steps}] {case_name} - {label}")

            status = str(step.get("status") or "").strip()
            if status:
                lines.append(f"状态: {status}")
            message = str(step.get("message") or "").strip()
            if message:
                lines.append(f"消息: {message}")

            operation = str(data.get("operation") or step.get("action") or step.get("kind") or "").strip()
            if operation:
                lines.append(f"操作: {operation}")

            command = _command_text(data)
            if command:
                lines.append(f"命令: {command}")
            rate_text = _rate_text(data)
            if rate_text:
                lines.append(f"速率: {rate_text}")
            stdout_text = _stream_text(data, "stdout")
            stderr_text = _stream_text(data, "stderr")
            if stdout_text:
                lines.append(f"stdout: {stdout_text}")
            if stderr_text:
                lines.append(f"stderr: {stderr_text}")
            nested_results = _nested_command_results_text(data)
            if nested_results:
                lines.append(nested_results)
            return_text = _return_text(step, data)
            if return_text:
                lines.append(f"返回: {return_text}")

            warnings = _step_warnings(data)
            if case_warnings and not case_warnings_printed:
                warnings.extend(case_warnings)
                case_warnings_printed = True
            for warning in warnings:
                lines.append(f"警告: {warning}")

            for artifact_path in _artifact_paths(step):
                lines.append(f"产物: {artifact_path}")
            for artifact_path in _data_artifact_paths(data):
                lines.append(f"产物: {artifact_path}")
            live_tail = _live_log_tail(data, step)
            if live_tail:
                lines.append(f"实时日志:\n{live_tail}")
            lines.append("")

    return "\n".join(lines).rstrip()


def _case_total_steps(case: dict[str, Any]) -> int:
    recorded = len(case.get("step_records") or [])
    metadata = case.get("metadata") if isinstance(case.get("metadata"), dict) else {}
    planned = len(metadata.get("steps") or [])
    return max(recorded, planned)


def extract_step_rows(run: dict[str, Any] | None) -> list[dict[str, str]]:
    """Extract case/step rows from typed or legacy run dictionaries."""

    if not run:
        return []
    if run.get("case_records"):
        return _rows_from_case_records(run["case_records"])
    return _rows_from_legacy_results(run.get("results") or [])


def format_raw_json(value: Any) -> str:
    """Pretty-print data for the raw inspector."""

    return json.dumps(value or {}, ensure_ascii=False, indent=2)


def _step_label(step: dict[str, Any], data: dict[str, Any]) -> str:
    for value in (data.get("label"), step.get("label"), step.get("step_id"), step.get("kind")):
        text = str(value or "").strip()
        if text:
            return text
    return "-"


def _command_text(data: dict[str, Any]) -> str:
    command = data.get("command")
    if command:
        return _stringify_console_value(command)
    commands = data.get("commands")
    if commands:
        return _stringify_console_value(commands)
    return ""


def _return_text(step: dict[str, Any], data: dict[str, Any]) -> str:
    for key in ("return_preview", "result_preview", "message"):
        value = data.get(key)
        if value:
            return _stringify_console_value(value)
    message = step.get("message")
    if message:
        return _stringify_console_value(message)
    return ""


def _rate_text(data: dict[str, Any]) -> str:
    bandwidth = data.get("bandwidth_mbps")
    rate_line = str(data.get("rate_line") or "").strip()
    parts = []
    if bandwidth not in (None, ""):
        parts.append(f"{bandwidth} Mbps")
    if rate_line:
        parts.append(rate_line)
    return " | ".join(parts)


def _stream_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not value:
        return ""
    return _stringify_console_value(value)


def _nested_command_results_text(data: dict[str, Any]) -> str:
    blocks: list[str] = []
    for key in ("results", "stopped"):
        values = data.get(key)
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values, start=1):
            if not isinstance(item, dict):
                continue
            lines = [f"鍛戒护缁撴灉[{index}]:"]
            command = item.get("command")
            if command:
                lines.append(f"input: {_stringify_console_value(command)}")
            stdout = item.get("stdout")
            if stdout not in (None, ""):
                lines.append(f"stdout: {_stringify_console_value(stdout)}")
            stderr = item.get("stderr")
            if stderr not in (None, ""):
                lines.append(f"stderr: {_stringify_console_value(stderr)}")
            exit_status = item.get("exit_status")
            if exit_status is not None:
                lines.append(f"exit_status: {exit_status}")
            local_path = item.get("local_path")
            if local_path:
                lines.append(f"local_path: {local_path}")
            if len(lines) > 1:
                blocks.append("\n".join(lines))
    return "\n".join(blocks)


def _step_warnings(data: dict[str, Any]) -> list[str]:
    warning = data.get("warning")
    if not warning:
        return []
    if isinstance(warning, list):
        return [str(item) for item in warning if str(item).strip()]
    return [str(warning)]


def _case_warnings(case: dict[str, Any]) -> list[str]:
    metadata = case.get("metadata") if isinstance(case.get("metadata"), dict) else {}
    warnings = metadata.get("warnings")
    if not warnings:
        return []
    if isinstance(warnings, list):
        return [str(item) for item in warnings if str(item).strip()]
    return [str(warnings)]


def _artifact_paths(step: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for artifact in step.get("artifacts") or []:
        if isinstance(artifact, dict):
            path = artifact.get("path")
        else:
            path = artifact
        text = str(path or "").strip()
        if text:
            paths.append(text)
    return paths


def _data_artifact_paths(data: dict[str, Any]) -> list[str]:
    paths = []
    for key in ("local_path", "local_log_path", "local_pcap_path", "output_path", "downloaded_path"):
        text = str(data.get(key) or "").strip()
        if text:
            paths.append(text)
    return paths


def _live_log_tail(data: dict[str, Any], step: dict[str, Any], *, max_lines: int = 20) -> str:
    path = _first_log_path(data, step)
    if path is None:
        return ""
    if path.suffix.lower() != ".log" or not path.exists() or not path.is_file():
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = deque(handle, maxlen=max_lines)
    except OSError:
        return ""
    return "".join(lines).strip()


def _first_log_path(data: dict[str, Any], step: dict[str, Any]) -> Path | None:
    for value in (data.get("local_path"), data.get("local_log_path")):
        text = str(value or "").strip()
        if text:
            return Path(text)
    for artifact in step.get("artifacts") or []:
        if isinstance(artifact, dict):
            text = str(artifact.get("path") or "").strip()
        else:
            text = str(artifact or "").strip()
        if text and Path(text).suffix.lower() == ".log":
            return Path(text)
    return None


def _console_cases(run: dict[str, Any]) -> list[dict[str, Any]]:
    cases = run.get("case_records") or []
    if cases:
        return cases
    return [_legacy_result_as_case(result) for result in run.get("results") or []]


def _legacy_result_as_case(result: dict[str, Any]) -> dict[str, Any]:
    case_name = str(result.get("name") or result.get("case_id") or "-")
    step_records: list[dict[str, Any]] = []
    for index, step in enumerate(result.get("steps") or [], start=1):
        if isinstance(step, dict):
            data = step.get("data") if isinstance(step.get("data"), dict) else {}
            step_records.append(
                {
                    "step_id": str(step.get("step_id") or f"step-{index}"),
                    "kind": str(step.get("kind") or step.get("step_id") or f"step-{index}"),
                    "status": str(step.get("status") or result.get("status") or "-"),
                    "message": str(step.get("message") or ""),
                    "data": data,
                    "artifacts": list(step.get("artifacts") or []),
                }
            )
        else:
            step_records.append(
                {
                    "step_id": f"step-{index}",
                    "kind": f"step-{index}",
                    "status": str(result.get("status") or ("passed" if result.get("passed") else "failed")),
                    "message": str(step),
                    "data": {"return_preview": str(step)},
                    "artifacts": [],
                }
            )
    if not step_records and result:
        step_records.append(
            {
                "step_id": case_name,
                "kind": case_name,
                "status": str(result.get("status") or ("passed" if result.get("passed") else "failed")),
                "message": str(result.get("error") or ""),
                "data": {},
                "artifacts": [],
            }
        )
    return {
        "name": case_name,
        "case_id": result.get("case_id"),
        "metadata": result.get("metadata") or {},
        "step_records": step_records,
    }


def _stringify_console_value(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if isinstance(value, tuple):
        return "\n".join(str(item) for item in value)
    return str(value)


def _rows_from_case_records(cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in cases:
        case_name = str(case.get("name") or case.get("case_id") or "-")
        for step in case.get("step_records") or []:
            rows.append(
                {
                    "case": case_name,
                    "step": str(step.get("step_id") or step.get("kind") or "-"),
                    "adapter": str(step.get("adapter") or "-"),
                    "status": str(step.get("status") or "-"),
                    "message": str(step.get("message") or ""),
                    "error": format_error(step.get("error")),
                }
            )
    return rows


def _rows_from_legacy_results(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        case_name = str(result.get("name") or result.get("case_id") or "-")
        steps = result.get("steps") or []
        if not steps:
            rows.append(
                {
                    "case": case_name,
                    "step": case_name,
                    "adapter": "-",
                    "status": str(result.get("status") or ("passed" if result.get("passed") else "failed")),
                    "message": str(result.get("error") or ""),
                    "error": format_error(result.get("error")),
                }
            )
            continue
        for index, step in enumerate(steps, start=1):
            rows.append(
                {
                    "case": case_name,
                    "step": f"step-{index}",
                    "adapter": "-",
                    "status": str(result.get("status") or "-"),
                    "message": str(step),
                    "error": "",
                }
            )
    return rows
