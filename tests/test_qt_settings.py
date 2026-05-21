import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.settings = {
            "base_web": {"host": "192.168.13.236", "password": "web-pass"},
            "ssh": {"host": "192.168.13.236"},
            "traffic": {"server_host": "10.88.149.164"},
            "common": {"delay_seconds": 5},
        }
        self.saved = []

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return []

    def load_settings(self):
        return self.settings

    def list_runs(self, limit=20):
        return []

    def save_settings(self, settings):
        self.saved.append(settings)
        self.settings = settings
        return settings


def test_settings_page_saves_one_group_without_replacing_siblings():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    window = MainWindow(controller=controller, start_polling=False)

    window.settings_page.set_field_value("base_web", "host", "192.168.13.250")
    window.settings_page.save_group("base_web")

    assert controller.saved
    assert controller.settings["base_web"]["host"] == "192.168.13.250"
    assert controller.settings["traffic"]["server_host"] == "10.88.149.164"
    window.close()
