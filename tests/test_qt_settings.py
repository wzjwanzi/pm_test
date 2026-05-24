import os
import json

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

    def export_settings(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.settings, handle, ensure_ascii=False, indent=2)
        return path

    def import_settings(self, path):
        with open(path, encoding="utf-8") as handle:
            self.settings = json.load(handle)
        self.saved.append(self.settings)
        return self.settings


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


def test_settings_page_exports_and_imports_full_config(tmp_path):
    QApplication.instance() or QApplication([])
    controller = FakeController()
    window = MainWindow(controller=controller, start_polling=False)

    export_path = tmp_path / "mobile_platform_config.json"
    window.settings_page.export_config_to_path(export_path)

    data = json.loads(export_path.read_text(encoding="utf-8"))
    assert data["traffic"]["server_host"] == "10.88.149.164"

    data["traffic"]["server_host"] = "192.168.13.164"
    data["traffic"]["phone_uplink_port"] = 7011
    export_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    imported = window.settings_page.import_config_from_path(export_path)

    assert imported["traffic"]["server_host"] == "192.168.13.164"
    assert controller.settings["traffic"]["phone_uplink_port"] == 7011
    assert window.settings_page.field_widgets["traffic"]["server_host"].text() == "192.168.13.164"
    window.close()


def test_settings_page_shows_config_file_actions_as_first_card():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    assert window.settings_page.config_file_card.title() == "配置文件"
    assert window.settings_page.export_button.text() == "导出配置"
    assert window.settings_page.import_button.text() == "导入配置"

    window.close()


def test_settings_page_keeps_traffic_card_to_server_connection_only():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    assert tuple(window.settings_page.field_widgets["traffic"]) == (
        "server_host",
        "server_username",
        "server_password",
    )
    assert "device_mapping" not in window.settings_page.field_widgets
    assert "server_downlink_target" not in window.settings_page.field_widgets["traffic"]
    assert "phone_uplink_target" not in window.settings_page.field_widgets["traffic"]

    window.close()
