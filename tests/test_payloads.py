from pm_tests.core.models import StepRecord, Status
from pm_tests.core.payloads import externalize_large_step_payloads


def make_step(data: dict) -> StepRecord:
    return StepRecord(
        step_id="pre_snapshot",
        kind="snapshot",
        adapter="snapshot",
        status=Status.PASSED,
        started_at="2026-05-15T00:00:00Z",
        data=data,
    )


def test_externalize_large_nested_string_to_payload_file(tmp_path):
    large = "radio-state-" * 500
    step = make_step({"network_info": {"network_type": large, "success": True}})

    externalize_large_step_payloads(step, tmp_path, threshold=100)

    reference = step.data["network_info"]["network_type"]
    assert reference["type"] == "external_payload"
    assert reference["path"] == "payloads/pre_snapshot/network_info-network_type.txt"
    assert reference["bytes"] == len(large.encode("utf-8"))
    assert reference["characters"] == len(large)
    assert reference["preview"].startswith("radio-state-")
    payload_path = tmp_path / reference["path"]
    assert payload_path.read_text(encoding="utf-8") == large


def test_externalize_preserves_short_strings(tmp_path):
    step = make_step({"message": "short"})

    externalize_large_step_payloads(step, tmp_path, threshold=100)

    assert step.data["message"] == "short"
    assert not (tmp_path / "payloads").exists()


def test_externalize_adds_artifact_record_for_payload(tmp_path):
    step = make_step({"cell_info": {"cell_info": "cell-" * 200}})

    externalize_large_step_payloads(step, tmp_path, threshold=100)

    assert len(step.artifacts) == 1
    artifact = step.artifacts[0]
    assert artifact.kind == "external_payload"
    assert artifact.path == "payloads/pre_snapshot/cell_info-cell_info.txt"
    assert artifact.label == "cell_info.cell_info"
    assert artifact.metadata["bytes"] == len(("cell-" * 200).encode("utf-8"))
