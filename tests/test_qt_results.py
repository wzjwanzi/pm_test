import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return []

    def load_settings(self):
        return {"base_web": {}, "ssh": {}, "traffic": {}, "common": {}}

    def list_runs(self, limit=20):
        return []


def test_results_page_renders_command_streams_and_artifacts():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    run = {
        "run_id": "run-1",
        "status": "running",
        "case_records": [
            {
                "name": "case",
                "step_records": [
                    {
                        "step_id": "ssh-1",
                        "kind": "base_ssh_command_start",
                        "status": "passed",
                        "data": {"command": "odi show", "stdout": "ok output", "stderr": "warn output"},
                        "artifacts": [{"path": r"D:\ssh_log\run-1.log"}],
                    }
                ],
            }
        ],
    }

    window.results_page.render_run(run)

    text = window.results_page.log_text.toPlainText()
    assert "odi show" in text
    assert "ok output" in text
    assert "warn output" in text
    assert r"D:\ssh_log\run-1.log" in text
    window.close()
