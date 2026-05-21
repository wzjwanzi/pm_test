import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.case_models import CaseStep, SavedCase
from desktop_qt.main_window import MainWindow


def _case():
    return SavedCase.new("下行灌包", [CaseStep.new("traffic_server_downlink_start", "server downlink", {})])


def _settings(*, target="10.6.251.27"):
    return {
        "base_web": {},
        "ssh": {},
        "traffic": {
            "server_host": "10.88.149.164",
            "server_password": "traffic-pass",
            "server_downlink_target": target,
        },
        "common": {},
    }


class FakeController:
    def __init__(self, settings):
        self.settings = settings
        self.created = None

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [_case().to_dict()]

    def load_settings(self):
        return self.settings

    def list_runs(self, limit=20):
        return []

    def case_to_run_payload(self, item):
        return item.to_dict()

    def create_run(self, device_id, cases):
        self.created = (device_id, cases)
        return {"success": True, "run": {"run_id": "run-1", "device_id": device_id, "status": "queued"}}


def test_home_blocks_start_when_required_config_missing():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings(target=""))
    window = MainWindow(controller=controller, start_polling=False)

    window.home_page.start_run()

    assert controller.created is None
    assert "下行灌包缺少服务器下行目标 IP" in window.home_page.message_label.text()
    window.close()


def test_home_creates_run_when_readiness_passes():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings())
    window = MainWindow(controller=controller, start_polling=False)

    window.home_page.start_run()

    assert controller.created is not None
    assert controller.created[0] == "device-1"
    assert controller.created[1][0]["name"] == "下行灌包"
    assert window.state.selected_run_id == "run-1"
    window.close()
