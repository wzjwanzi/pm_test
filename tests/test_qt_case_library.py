import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.case_models import CaseStep, SavedCase
from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.case = SavedCase.new("custom-downlink", [CaseStep.new("traffic_server_downlink_start", "server downlink", {})])

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [self.case.to_dict()]

    def get_step_templates(self):
        return [
            {
                "action": "traffic_server_downlink_start",
                "label": "开始下行灌包",
                "group": "灌包服务器",
                "fields": [
                    {"name": "iperf_bandwidth", "label": "带宽", "type": "text"},
                    {"name": "iperf_duration", "label": "时长", "type": "int"},
                ],
                "defaults": {},
            },
            {
                "action": "base_ssh_command_once",
                "label": "执行命令",
                "group": "基站 SSH",
                "fields": [{"name": "command", "label": "SSH 命令", "type": "text"}],
                "defaults": {},
            },
            {
                "action": "traffic_server_uplink_receive_start",
                "label": "开始上行接收",
                "group": "灌包服务器",
                "fields": [{"name": "iperf_port", "label": "端口", "type": "int"}],
                "defaults": {},
            },
            {
                "action": "phone_downlink_receive_start",
                "label": "开始下行接收",
                "group": "手机",
                "fields": [{"name": "iperf_port", "label": "端口", "type": "int"}],
                "defaults": {},
            },
        ]

    def load_settings(self):
        return {
            "base_web": {},
            "ssh": {},
            "traffic": {
                "server_host": "10.88.149.164",
                "server_password": "pass",
                "server_downlink_target": "10.6.251.27",
                "server_downlink_bandwidth": "120m",
                "server_downlink_duration": 60000,
            },
            "common": {},
        }

    def list_runs(self, limit=20):
        return []


def test_case_library_adds_selected_case_to_home_run_selection():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    window.case_library_page.case_list.setCurrentRow(0)
    window.case_library_page.add_selected_to_run()

    assert window.state.selected_case.name == "custom-downlink"
    assert window.home_page.selected_case().name == "custom-downlink"
    window.close()


def test_case_library_has_operation_library_grouped_by_business_area():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)

    groups = window.case_library_page.available_operation_groups()

    assert "灌包服务器" in groups
    assert "基站 SSH" in groups
    assert window.case_library_page.operation_list.count() == 4
    window.close()


def test_clicking_operation_shows_global_default_parameters_and_adds_local_step():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page

    page.select_operation("traffic_server_downlink_start")

    assert page.parameter_value("iperf_bandwidth") == "120m"

    page.set_parameter_value("iperf_bandwidth", "250m")
    page.add_operation_to_case()

    case = page.selected_case()
    assert case.steps[-1].action == "traffic_server_downlink_start"
    assert case.steps[-1].params["iperf_bandwidth"] == "250m"
    assert case.steps[-1].params["command"].find("-b 250m") >= 0
    window.close()


def test_clicking_case_step_edits_that_step_local_parameters():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page
    page.select_operation("traffic_server_downlink_start")
    page.set_parameter_value("iperf_bandwidth", "250m")
    page.add_operation_to_case()

    page.step_list.setCurrentRow(page.step_list.count() - 1)
    page.set_parameter_value("iperf_bandwidth", "300m")
    page.save_selected_step_parameters()

    case = page.selected_case()
    assert case.steps[-1].params["iperf_bandwidth"] == "300m"
    assert case.steps[-1].params["command"].find("-b 300m") >= 0
    window.close()


def test_delete_selected_step_removes_operation_from_case():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page
    page.select_operation("traffic_server_downlink_start")
    page.add_operation_to_case()
    case = page.selected_case()
    before = len(case.steps)

    page.step_list.setCurrentRow(page.step_list.count() - 1)
    page.delete_selected_step()

    assert len(case.steps) == before - 1
    assert page.step_list.count() == len(case.steps)
    window.close()


def test_receive_operations_do_not_show_bandwidth_parameters():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page

    page.select_operation("traffic_server_uplink_receive_start")
    assert "iperf_bandwidth" not in page.parameter_widgets
    assert "iperf_duration" not in page.parameter_widgets

    page.select_operation("phone_downlink_receive_start")
    assert "iperf_bandwidth" not in page.parameter_widgets
    assert "iperf_duration" not in page.parameter_widgets
    window.close()
