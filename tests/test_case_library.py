from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase
import config


def test_case_library_create_load_rename_copy_delete(tmp_path):
    library = CaseLibrary(tmp_path)
    case = SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {"count": 3})])

    path = library.save(case)
    loaded = library.load(path.name)
    renamed = library.rename(loaded.case_id, "renamed")
    copied = library.copy_case(renamed.case_id, "copy1")
    library.delete(renamed.case_id)

    assert not path.exists()
    assert loaded.name == "test1"
    assert renamed.name == "renamed"
    assert copied.name == "copy1"
    assert [item.name for item in library.list_cases()] == ["copy1"]


def test_case_library_defaults_to_runtime_cases_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CASES_DIR", tmp_path / "cases")

    library = CaseLibrary()
    case = SavedCase.new("persisted", [CaseStep.new("phone_ping", "手机-ping", {})])
    library.save(case)

    reopened = CaseLibrary()
    assert reopened.root == tmp_path / "cases"
    assert [item.name for item in reopened.list_cases()] == ["persisted"]


def test_duplicate_visible_names_have_distinct_files(tmp_path):
    library = CaseLibrary(tmp_path)

    first = library.save(SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {})]))
    second = library.save(SavedCase.new("test1", [CaseStep.new("phone_ping", "手机-ping", {})]))

    assert first.name != second.name
    assert len(library.list_cases()) == 2


def test_list_cases_sorts_by_name_then_case_id(tmp_path):
    library = CaseLibrary(tmp_path)
    case_b = SavedCase.new("b", [CaseStep.new("phone_ping", "手机-ping", {})])
    case_a2 = SavedCase.new("a", [CaseStep.new("phone_ping", "手机-ping", {})])
    case_a1 = SavedCase.new("a", [CaseStep.new("phone_ping", "手机-ping", {})])
    case_a1.case_id = "case_00000001"
    case_a2.case_id = "case_00000002"
    case_b.case_id = "case_00000000"

    library.save(case_b)
    library.save(case_a2)
    library.save(case_a1)

    assert [(item.name, item.case_id) for item in library.list_cases()] == [
        ("a", "case_00000001"),
        ("a", "case_00000002"),
        ("b", "case_00000000"),
    ]


def test_safe_filename_and_load_by_case_id(tmp_path):
    library = CaseLibrary(tmp_path)
    case = SavedCase.new("中文:bad/name*?", [CaseStep.new("phone_ping", "手机-ping", {})])

    path = library.save(case)
    loaded = library.load(case.case_id)
    raw_json = path.read_text(encoding="utf-8")

    assert path.name.endswith(f"-{case.case_id}.json")
    assert ":" not in path.name
    assert "/" not in path.name
    assert "*" not in path.name
    assert "中文:bad/name*?" in raw_json
    assert "\\u4e2d" not in raw_json
    assert loaded.case_id == case.case_id
    assert loaded.name == "中文:bad/name*?"


def test_rename_removes_stale_file_after_new_file_is_written(tmp_path):
    library = CaseLibrary(tmp_path)
    case = SavedCase.new("old-name", [CaseStep.new("phone_ping", "手机-ping", {})])

    old_path = library.save(case)
    renamed = library.rename(case.case_id, "new-name")
    new_path = library.load(renamed.case_id)

    assert not old_path.exists()
    assert new_path.name == "new-name"
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_rename_keeps_old_file_when_new_write_fails(tmp_path, monkeypatch):
    library = CaseLibrary(tmp_path)
    case = SavedCase.new("old-name", [CaseStep.new("phone_ping", "手机-ping", {})])
    old_path = library.save(case)

    def fail_write(path, saved_case):
        if path != old_path:
            raise OSError("disk full")
        library.__class__._write(library, path, saved_case)

    monkeypatch.setattr(library, "_write", fail_write)

    try:
        library.rename(case.case_id, "new-name")
    except OSError as exc:
        assert "disk full" in str(exc)
    else:
        raise AssertionError("rename should fail when the new file cannot be written")

    assert old_path.exists()
    assert library.load(case.case_id).name == "old-name"


def test_copy_case_preserves_step_data_with_new_case_identity(tmp_path):
    library = CaseLibrary(tmp_path)
    source = SavedCase.new(
        "source",
        [CaseStep.new("phone_ping", "手机-ping", {"count": 3})],
        description="desc",
    )
    source.created_at = "2026-01-01T00:00:00"
    source.updated_at = "2026-01-01T00:00:00"
    library.save(source)

    copied = library.copy_case(source.case_id, "copy1")

    assert copied.case_id != source.case_id
    assert copied.created_at != source.created_at
    assert copied.updated_at != source.updated_at
    assert copied.description == "desc"
    assert copied.steps[0].action == "phone_ping"
    assert copied.steps[0].label == "手机-ping"
    assert copied.steps[0].params == {"count": 3}
