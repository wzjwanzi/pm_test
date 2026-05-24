import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.settings = {
            "base_web": {},
            "ssh": {},
            "traffic": {
                "server_host": "192.168.13.164",
                "server_downlink_bandwidth": "250m",
                "server_downlink_duration": 60000,
                "phone_uplink_bandwidth": "120m",
                "phone_uplink_duration": 6000,
                "device_overrides": {},
            },
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
    window.devices_page.ping_count_edit.setText("0")
    window.devices_page.save_mapping()

    saved = controller.settings["traffic"]["device_overrides"]["device-1"]
    assert saved["phone_ip"] == "10.6.251.27"
    assert saved["downlink_port"] == 6011
    assert saved["uplink_port"] == 7011
    assert saved["server_downlink_target"] == "10.6.251.27"
    assert saved["server_ping_target"] == "10.6.251.27"
    assert saved["phone_downlink_listen_port"] == 6011
    assert saved["server_downlink_port"] == 6011
    assert saved["server_uplink_listen_port"] == 7011
    assert saved["phone_uplink_port"] == 7011
    assert saved["traffic_server_ip"] == "10.88.149.164"
    assert saved["phone_uplink_target"] == "10.88.149.164"
    assert saved["server_ping_count"] == 0
    window.close()


def test_devices_page_loads_existing_mapping_when_device_is_selected():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    controller.settings["traffic"]["device_overrides"] = {
        "device-1": {
            "phone_ip": "10.6.251.27",
            "downlink_port": 6011,
            "uplink_port": 7011,
            "phone_uplink_target": "10.88.149.164",
            "server_downlink_bandwidth": "250m",
            "phone_uplink_bandwidth": "120m",
            "server_ping_count": 3,
        }
    }
    window = MainWindow(controller=controller, start_polling=False)

    assert window.devices_page.phone_ip_edit.text() == "10.6.251.27"
    assert window.devices_page.downlink_port_edit.text() == "6011"
    assert window.devices_page.uplink_port_edit.text() == "7011"
    assert window.devices_page.server_ip_edit.text() == "10.88.149.164"
    assert window.devices_page.downlink_bandwidth_edit.text() == "250m"
    assert window.devices_page.uplink_bandwidth_edit.text() == "120m"
    assert window.devices_page.ping_count_edit.text() == "3"
    window.close()


def test_devices_page_refresh_includes_configured_offline_devices():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    controller.settings["traffic"]["device_overrides"] = {
        "offline-device": {"phone_ip": "10.6.251.29"}
    }
    window = MainWindow(controller=controller, start_polling=False)

    items = [window.devices_page.device_list.item(index).text() for index in range(window.devices_page.device_list.count())]

    assert items == ["device-1", "offline-device"]
    window.close()


def test_devices_page_uses_left_middle_right_columns():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    window = MainWindow(controller=controller, start_polling=False)

    page = window.devices_page

    assert page.layout().itemAt(0).widget() is page.left_panel
    assert page.layout().itemAt(1).widget() is page.middle_panel
    assert page.layout().itemAt(2).widget() is page.right_panel
    assert page.middle_panel.layout().itemAt(1).widget() is page.device_list
    assert page.right_panel.layout().itemAt(0).layout() is page.mapping_form
    window.close()
