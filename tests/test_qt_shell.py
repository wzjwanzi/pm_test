import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [{"name": "下行灌包", "steps": [{"action": "traffic_server_downlink_start"}]}]

    def load_settings(self):
        return {"traffic": {}, "base_web": {}, "ssh": {}, "common": {}}

    def list_runs(self, limit=20):
        return []


def test_main_window_has_base_station_config_navigation_entry():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    labels = [window.nav_list.item(index).text() for index in range(window.nav_list.count())]

    assert labels == ["首页运行", "用例库", "基站配置", "设备管理", "运行配置", "结果日志"]
    assert window.stack.currentWidget() is window.home_page
    window.close()
