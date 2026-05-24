import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


def test_qt_desktop_preview_builds_current_workbench_pages():
    QApplication.instance() or QApplication([])
    window = MainWindow(start_polling=False)

    try:
        labels = [window.nav_list.item(index).text() for index in range(window.nav_list.count())]

        assert labels == ["首页运行", "用例库", "基站配置", "设备管理", "运行配置", "结果日志"]
        assert window.stack.count() == 6
        assert hasattr(window, "home_page")
        assert hasattr(window, "case_library_page")
        assert hasattr(window, "base_station_config_page")
        assert hasattr(window, "devices_page")
        assert hasattr(window, "settings_page")
    finally:
        window.close()
