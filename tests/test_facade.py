import config
from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase
from pm_tests.core.facade import PmTestRunManager


def test_facade_creates_and_lists_runs(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    run = manager.create_run(
        "device-1",
        cases=[{"name": "case", "host": "10.0.0.1", "count": 1, "ping_enabled": False}],
    )

    assert run["success"] is True
    assert run["run"]["device_id"] == "device-1"
    assert manager.get_run(run["run"]["run_id"])["run_id"] == run["run"]["run_id"]
    assert manager.list_runs(limit=1)[0]["run_id"] == run["run"]["run_id"]


def test_facade_templates_are_available(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    templates = manager.get_templates()

    assert templates
    assert templates[0]["name"] == "下行灌包"
    assert templates[0]["steps"][0]["action"] == "base_web_capture_start"


def test_facade_uses_saved_case_library_as_templates(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CASES_DIR", tmp_path / "cases")
    library = CaseLibrary()
    for name in ["library-a", "library-b", "library-c", "library-d"]:
        library.save(
            SavedCase.new(
                name,
                [CaseStep.new("phone_ping", "ping", {"host": "10.0.0.1", "count": 1})],
            )
        )
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    templates = manager.get_templates()

    assert {item["name"] for item in templates} == {"library-a", "library-b", "library-c", "library-d"}
    assert all(item["steps"] for item in templates)


def test_facade_creates_run_from_explicit_saved_case(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    run = manager.create_run(
        "device-1",
        cases=[
            {
                "case_id": "case_saved",
                "name": "saved",
                "steps": [
                    {
                        "step_id": "s1",
                        "action": "base_web_capture_start",
                        "label": "capture",
                        "enabled": True,
                        "params": {"capture_fapi_interface": "FAPI1"},
                    }
                ],
            }
        ],
    )

    step = run["run"]["case_records"][0]["step_records"][0]
    assert run["success"] is True
    assert run["run"]["case_records"][0]["case_id"] == "case_saved"
    assert step["data"]["action"] == "base_web_capture_start"
    assert step["data"]["label"] == "capture"


def test_facade_creates_run_from_mixed_explicit_and_legacy_cases(tmp_path):
    manager = PmTestRunManager(artifacts_root=tmp_path, run_async=False)

    run = manager.create_run(
        "device-1",
        cases=[
            {
                "name": "saved",
                "steps": [
                    {
                        "step_id": "s1",
                        "action": "phone_ping",
                        "label": "手机 ping",
                        "enabled": True,
                        "params": {"host": "10.0.0.1", "count": 1},
                    }
                ],
            },
            {"name": "legacy", "host": "10.0.0.2", "count": 1, "ping_enabled": True},
        ],
    )

    cases = run["run"]["case_records"]

    assert [item["name"] for item in cases] == ["saved", "legacy"]
    assert len(cases[0]["step_records"]) == 1
    assert len(cases[1]["step_records"]) > 0
