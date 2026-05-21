import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.case_models import CaseStep, SavedCase
from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.case = SavedCase.new("自定义下行", [CaseStep.new("traffic_server_downlink_start", "server downlink", {})])

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [self.case.to_dict()]

    def load_settings(self):
        return {
            "base_web": {},
            "ssh": {},
            "traffic": {"server_host": "10.88.149.164", "server_password": "pass", "server_downlink_target": "10.6.251.27"},
            "common": {},
        }

    def list_runs(self, limit=20):
        return []


def test_case_library_adds_selected_case_to_home_run_selection():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    window.case_library_page.case_list.setCurrentRow(0)
    window.case_library_page.add_selected_to_run()

    assert window.state.selected_case.name == "自定义下行"
    assert window.home_page.selected_case().name == "自定义下行"
    window.close()
