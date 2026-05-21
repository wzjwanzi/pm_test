import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.settings = {
            "base_web": {},
            "ssh": {},
            "traffic": {"device_overrides": {}},
            "common": {},
        }

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return []

    def load_settings(self):
        return self.settings

    def list_runs(self, limit=20):
        return []

    def save_settings(self, settings):
        self.settings = settings
        return settings


def test_devices_page_persists_device_phone_ip_mapping():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    window = MainWindow(controller=controller, start_polling=False)

    window.devices_page.set_mapping("device-1", phone_ip="10.6.251.27", downlink_port="6011", uplink_port="7011")
    window.devices_page.save_mapping()

    saved = controller.settings["traffic"]["device_overrides"]["device-1"]
    assert saved["phone_ip"] == "10.6.251.27"
    assert saved["downlink_port"] == 6011
    assert saved["uplink_port"] == 7011
    window.close()
