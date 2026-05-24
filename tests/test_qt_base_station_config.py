import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.saved = None
        self.read_count = 0
        self.common_read_count = 0

    def refresh_devices(self):
        return []

    def get_templates(self):
        return []

    def load_settings(self):
        return {"base_web": {"host": "192.168.13.236", "port": 8400}, "ssh": {}, "traffic": {}, "common": {}}

    def list_runs(self, limit=20):
        return []

    def discover_base_station_nodes(self):
        return [{"path": "Device.Services.FAPService.1.CellConfig.1.", "label": "Cell 1"}]

    def get_base_station_node_parameters(self, node):
        self.read_count += 1
        assert node == "Device.Services.FAPService.1.CellConfig.1."
        return {
            "NR.RAN.Common.CellIdWithinGnb": "1",
            "NR.RAN.RF.PhyCellID": "236",
        }

    def get_base_station_common_parameters(self, node):
        self.common_read_count += 1
        assert node == "Device.Services.FAPService.1.CellConfig.1."
        return {
            "CellIdWithinGnb": "1",
            "PhyCellID": "236",
        }

    def set_base_station_node_parameters(self, node, values):
        self.saved = (node, values)
        return {"success": True, "code": "200"}

    def set_base_station_common_parameters(self, node, values):
        self.saved = (node, values)
        return {"success": True, "code": "200"}


def test_base_station_config_page_loads_nodes_and_saves_changed_values_only():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    window = MainWindow(controller=controller, start_polling=False)

    page = window.base_station_config_page
    page.refresh_nodes()
    assert page.category_list.count() == 2
    assert page.node_list.count() == 1
    assert controller.read_count == 0
    assert controller.common_read_count == 0
    assert page.param_table.rowCount() == 0
    assert "读取参数" in page.status_label.text()

    page.load_current_node()
    assert page.param_table.rowCount() == 2
    assert controller.read_count == 0
    assert controller.common_read_count == 1

    for row in range(page.param_table.rowCount()):
        if page.param_table.item(row, 0).text() == "PhyCellID":
            page.param_table.item(row, 1).setText("237")
    page.save_changes()

    assert controller.saved == (
        "Device.Services.FAPService.1.CellConfig.1.",
        {"PhyCellID": "237"},
    )
    assert "保存完成" in page.status_label.text()
    window.close()
