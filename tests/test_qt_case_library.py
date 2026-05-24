import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from desktop.case_models import CaseStep, SavedCase
from desktop.case_templates import build_default_case_templates
from desktop_qt.main_window import MainWindow


class FakeController:
    def __init__(self):
        self.settings = {
            "base_web": {
                "host": "192.168.13.236",
                "port": 8400,
                "username": "root",
                "password": "pass",
                "log_download_dir": r"D:\logs",
                "capture_signal_enabled": True,
                "capture_data_enabled": False,
                "capture_fapi_interface": "FAPI1",
            },
            "ssh": {},
            "traffic": {
                "server_host": "192.168.13.164",
                "server_password": "pass",
                "server_downlink_target": "10.6.251.27",
                "server_downlink_bandwidth": "120m",
                "server_downlink_duration": 60000,
            },
            "common": {},
        }
        self.case = SavedCase.new(
            "custom-downlink",
            [
                CaseStep.new("base_web_capture_start", "capture", {}),
                CaseStep.new("traffic_server_downlink_start", "server downlink", {}),
            ],
        )

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [self.case.to_dict()]

    def get_step_templates(self):
        return [
            {
                "action": "base_web_capture_start",
                "label": "开始抓包",
                "group": "基站 Web",
                "fields": [
                    {"name": "capture_signal_enabled", "label": "抓取信令", "type": "bool"},
                    {"name": "capture_data_enabled", "label": "抓取数据", "type": "bool"},
                    {"name": "capture_fapi_interface", "label": "FAPI 接口", "type": "choice", "choices": ["无", "FAPI1", "FAPI3"]},
                ],
                "defaults": {},
            },
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
                "action": "common_delay",
                "label": "延时",
                "group": "通用",
                "fields": [{"name": "delay_seconds", "label": "延时秒数", "type": "int"}],
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
            {
                "action": "phone_uplink_iperf_start",
                "label": "开始上行灌包",
                "group": "手机",
                "fields": [
                    {"name": "iperf_port", "label": "端口", "type": "int"},
                    {"name": "iperf_bandwidth", "label": "带宽", "type": "text"},
                    {"name": "iperf_duration", "label": "时长", "type": "int"},
                ],
                "defaults": {},
            },
            {
                "action": "phone_uplink_iperf_stop",
                "label": "停止上行灌包",
                "group": "手机",
                "fields": [],
                "defaults": {},
            },
        ]

    def load_settings(self):
        return self.settings

    def save_settings(self, settings):
        self.settings = settings
        return settings

    def list_runs(self, limit=20):
        return []

    def case_to_run_payload(self, item):
        from desktop.case_operations import case_to_run_payload

        return case_to_run_payload(item, self.load_settings())


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
    assert window.case_library_page.operation_list.count() == 8
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
    assert case.steps[-1].param_overrides == {"iperf_bandwidth": "300m"}
    window.close()


def test_case_step_uses_current_global_defaults_unless_locally_overridden():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page
    page.select_operation("traffic_server_downlink_start")
    page.add_operation_to_case()
    step = page.selected_case().steps[-1]

    assert step.param_overrides == {}

    window.controller.load_settings = lambda: {
        "base_web": {},
        "ssh": {},
        "traffic": {
            "server_host": "10.88.149.200",
            "server_password": "pass",
            "server_downlink_target": "10.6.251.30",
            "server_downlink_bandwidth": "180m",
            "server_downlink_duration": 60000,
        },
        "common": {},
    }
    payload = window.controller.case_to_run_payload(page.selected_case())
    params = payload["steps"][-1]["params"]

    assert params["server_host"] == "10.88.149.200"
    assert params["iperf_bandwidth"] == "180m"
    assert "-b 180m" in params["command"]
    window.close()


def test_clicking_existing_case_step_shows_updated_operation_defaults():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page
    page.select_operation("traffic_server_downlink_start")
    page.add_operation_to_case()

    window.controller.load_settings = lambda: {
        "base_web": {},
        "ssh": {},
        "traffic": {
            "server_host": "192.168.13.164",
            "server_password": "pass",
            "server_downlink_target": "10.6.251.30",
            "server_downlink_bandwidth": "180m",
            "server_downlink_duration": 60000,
        },
        "common": {},
    }

    page.step_list.setCurrentRow(page.step_list.count() - 1)
    page.render_selected_step()

    assert page.parameter_value("iperf_bandwidth") == "180m"
    window.close()


def test_saving_operation_defaults_updates_existing_case_step_display():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page

    page.select_operation("base_web_capture_start")
    page.set_parameter_value("capture_fapi_interface", "无")
    page.save_selected_step_parameters()

    page.step_list.setCurrentRow(0)
    page.render_selected_step()

    assert window.controller.settings["base_web"]["capture_fapi_interface"] == "无"
    assert page.parameter_value("capture_fapi_interface") == "无"
    window.close()


def test_phone_uplink_operation_defaults_use_phone_port_and_persist_after_save():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    controller.settings["traffic"].update(
        {
            "server_downlink_port": 6011,
            "server_downlink_bandwidth": "250m",
            "phone_uplink_target": "10.88.149.164",
            "phone_uplink_port": 7011,
            "phone_uplink_bandwidth": "120m",
            "phone_uplink_duration": 6000,
        }
    )
    window = MainWindow(controller=controller, start_polling=False)
    page = window.case_library_page

    page.select_operation("phone_uplink_iperf_start")

    assert page.parameter_value("iperf_port") == "7011"
    assert page.parameter_value("iperf_bandwidth") == "120m"

    page.set_parameter_value("iperf_port", "7011")
    page.set_parameter_value("iperf_bandwidth", "120m")
    page.save_selected_step_parameters()

    assert controller.settings["traffic"]["phone_uplink_port"] == 7011
    assert controller.settings["traffic"]["phone_uplink_bandwidth"] == "120m"
    assert page.parameter_value("iperf_port") == "7011"
    assert page.parameter_value("iperf_bandwidth") == "120m"
    window.close()


def test_phone_uplink_stop_operation_has_no_parameters():
    QApplication.instance() or QApplication([])
    window = MainWindow(controller=FakeController(), start_polling=False)
    page = window.case_library_page

    page.select_operation("phone_uplink_iperf_stop")

    assert page.parameter_widgets == {}
    window.close()


def test_bidirectional_case_delay_step_override_is_used_in_run_payload():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    controller.settings["common"] = {"delay_seconds": 5}
    controller.case = next(item for item in build_default_case_templates(controller.settings) if item.name == "双向灌包")
    window = MainWindow(controller=controller, start_polling=False)
    page = window.case_library_page

    delay_index = next(index for index, step in enumerate(page.selected_case().steps) if step.action == "common_delay")
    page.step_list.setCurrentRow(delay_index)
    page.set_parameter_value("delay_seconds", "90")
    page.save_selected_step_parameters()

    case = page.selected_case()
    payload = controller.case_to_run_payload(case)
    delay_payload = next(step for step in payload["steps"] if step["step_id"] == case.steps[delay_index].step_id)

    assert case.steps[delay_index].param_overrides == {"delay_seconds": 90}
    assert delay_payload["params"]["delay_seconds"] == 90
    window.close()


def test_saving_case_step_updates_matching_home_case_copy():
    QApplication.instance() or QApplication([])
    controller = FakeController()
    controller.settings["common"] = {"delay_seconds": 5}
    controller.case = next(item for item in build_default_case_templates(controller.settings) if item.name == "双向灌包")
    window = MainWindow(controller=controller, start_polling=False)
    page = window.case_library_page

    delay_index = next(index for index, step in enumerate(page.selected_case().steps) if step.action == "common_delay")
    page.step_list.setCurrentRow(delay_index)
    page.set_parameter_value("delay_seconds", "90")
    page.save_selected_step_parameters()

    home_case = next(case for case in window.home_page.cases if case.name == "双向灌包")
    payload = controller.case_to_run_payload(home_case)
    delay_payload = next(step for step in payload["steps"] if step["step_id"] == page.selected_case().steps[delay_index].step_id)

    assert delay_payload["params"]["delay_seconds"] == 90
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
