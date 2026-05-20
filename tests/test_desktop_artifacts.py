from pathlib import Path

import pytest

from desktop.artifacts import (
    build_run_report,
    export_run_report,
    extract_external_payloads,
    open_artifact_dir,
)


def sample_run(artifact_dir: Path) -> dict:
    return {
        "run_id": "run-42",
        "device_id": "device-1",
        "status": "passed",
        "artifact_dir": str(artifact_dir),
        "summary": {"total": 1, "passed": 1, "failed": 0, "error": 0, "skipped": 0},
        "case_records": [
            {
                "name": "Ping Case",
                "step_records": [
                    {
                        "step_id": "phone_ping",
                        "adapter": "traffic",
                        "status": "passed",
                        "message": "Ping completed",
                    }
                ],
            }
        ],
    }


def sample_run_with_payloads(artifact_dir: Path) -> dict:
    run = sample_run(artifact_dir)
    run["case_records"][0]["step_records"][0]["artifacts"] = [
        {
            "kind": "external_payload",
            "path": "payloads/pre_snapshot/network_info-network_type.txt",
            "label": "network_info.network_type",
            "metadata": {"bytes": 57247, "characters": 57215},
        }
    ]
    return run


def test_build_run_report_creates_compact_markdown(tmp_path):
    report = build_run_report(sample_run(tmp_path))

    assert "# Run Report: run-42" in report
    assert "- Device: `device-1`" in report
    assert "- Status: `passed`" in report
    assert "- Passed: `1/1`" in report
    assert "| Ping Case | phone_ping | traffic | passed | Ping completed |  |" in report
    assert "{" not in report


def test_extract_external_payloads_returns_handoff_rows(tmp_path):
    rows = extract_external_payloads(sample_run_with_payloads(tmp_path))

    assert rows == [
        {
            "case": "Ping Case",
            "step": "phone_ping",
            "label": "network_info.network_type",
            "path": "payloads/pre_snapshot/network_info-network_type.txt",
            "bytes": "57247",
            "characters": "57215",
        }
    ]


def test_build_run_report_includes_external_payload_table(tmp_path):
    report = build_run_report(sample_run_with_payloads(tmp_path))

    assert "## External Payloads" in report
    assert "| Case | Step | Label | Path | Bytes | Characters |" in report
    assert "| Ping Case | phone_ping | network_info.network_type | payloads/pre_snapshot/network_info-network_type.txt | 57247 | 57215 |" in report


def test_export_run_report_writes_to_artifact_directory(tmp_path):
    output = export_run_report(sample_run(tmp_path))

    assert output == tmp_path / "run_report.md"
    assert output.exists()
    assert "run-42" in output.read_text(encoding="utf-8")


def test_open_artifact_dir_uses_injected_opener(tmp_path):
    opened = []

    result = open_artifact_dir(sample_run(tmp_path), opener=lambda path: opened.append(path))

    assert result == tmp_path
    assert opened == [tmp_path]


def test_open_artifact_dir_rejects_missing_artifact_dir():
    with pytest.raises(ValueError):
        open_artifact_dir({"run_id": "run-1"}, opener=lambda path: None)
