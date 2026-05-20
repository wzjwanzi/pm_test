from pathlib import Path

from pm_tests import base_ssh


def test_open_log_file_falls_back_to_artifacts_dir_when_output_dir_is_not_writable(monkeypatch, tmp_path):
    blocked = tmp_path / "blocked"
    fallback = tmp_path / "artifacts"
    monkeypatch.setattr(base_ssh.config, "PM_ARTIFACTS_DIR", fallback)
    original_open = Path.open

    def fake_open(path, *args, **kwargs):
        if str(path).startswith(str(blocked)):
            raise PermissionError("denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)

    handle, path, fallback_from = base_ssh._open_log_file(blocked, "rrc_cpu.log")
    try:
        handle.write("ok")
    finally:
        handle.close()

    assert path == fallback / "rrc_cpu.log"
    assert fallback_from == str(blocked)
    assert path.read_text(encoding="utf-8") == "ok"
