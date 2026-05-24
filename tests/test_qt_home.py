import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QAbstractItemView

from desktop.case_models import CaseStep, SavedCase
from desktop.case_templates import build_default_case_templates
from desktop_qt.main_window import MainWindow


def _case():
    return SavedCase.new("涓嬭鐏屽寘", [CaseStep.new("traffic_server_downlink_start", "server downlink", {})])


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
        self.created_runs = []
        self.run_detail = None

    def refresh_devices(self):
        return ["device-1"]

    def get_templates(self):
        return [_case().to_dict()]

    def load_settings(self):
        return self.settings

    def list_runs(self, limit=20):
        return []

    def get_run(self, run_id):
        return self.run_detail

    def case_to_run_payload(self, item):
        return item.to_dict()

    def create_run(self, device_id, cases):
        self.created = (device_id, cases)
        self.created_runs.append((device_id, cases))
        return {"success": True, "run": {"run_id": f"run-{len(self.created_runs)}", "device_id": device_id, "status": "queued"}}


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
    assert controller.created[1][0]["name"] == "涓嬭鐏屽寘"
    assert window.state.selected_run_id == "run-1"
    window.close()


def test_home_applies_selected_device_mapping_to_iperf_targets():
    QApplication.instance() or QApplication([])
    settings = _settings(target="")
    settings["base_web"] = {"host": "192.168.13.236", "password": "web-pass"}
    settings["ssh"] = {"host": "192.168.13.236", "password": "ssh-pass"}
    settings["traffic"].update(
        {
            "phone_uplink_target": "",
            "device_overrides": {
                "device-1": {
                    "phone_ip": "10.6.251.27",
                    "server_downlink_target": "10.6.251.27",
                    "phone_uplink_target": "192.168.13.164",
                    "server_downlink_port": 6011,
                    "phone_uplink_port": 7011,
                }
            },
        }
    )
    case = next(item for item in build_default_case_templates(settings) if len(item.steps) == 17)
    controller = FakeController(settings)
    controller.get_templates = lambda: [case.to_dict()]
    window = MainWindow(controller=controller, start_polling=False)

    window.home_page.start_run()

    payload = controller.created[1][0]
    downlink = next(step for step in payload["steps"] if step["action"] == "traffic_server_downlink_start")
    uplink = next(step for step in payload["steps"] if step["action"] == "phone_uplink_iperf_start")
    assert "-c 10.6.251.27" in downlink["params"]["command"]
    assert "-c 192.168.13.164" in uplink["params"]["command"]
    window.close()


def test_home_dual_phone_mode_creates_one_run_per_selected_device():
    QApplication.instance() or QApplication([])
    settings = _settings(target="")
    settings["base_web"] = {"host": "192.168.13.236", "password": "web-pass"}
    settings["ssh"] = {"host": "192.168.13.236", "password": "ssh-pass"}
    settings["traffic"].update(
        {
            "phone_uplink_target": "",
            "device_overrides": {
                "phone-a": {
                    "server_downlink_target": "10.6.251.27",
                    "phone_uplink_target": "192.168.13.164",
                    "server_downlink_port": 6011,
                    "phone_uplink_port": 7011,
                },
                "phone-b": {
                    "server_downlink_target": "10.6.251.28",
                    "phone_uplink_target": "192.168.13.164",
                    "server_downlink_port": 6012,
                    "phone_uplink_port": 7012,
                },
            },
        }
    )
    case = next(item for item in build_default_case_templates(settings) if len(item.steps) == 17)
    controller = FakeController(settings)
    controller.refresh_devices = lambda: ["phone-a", "phone-b"]
    controller.get_templates = lambda: [case.to_dict()]
    window = MainWindow(controller=controller, start_polling=False)
    window.home_page.run_mode_combo.setCurrentIndex(1)
    for row in range(window.home_page.device_list.count()):
        window.home_page.device_list.item(row).setSelected(True)

    window.home_page.start_run()

    assert [item[0] for item in controller.created_runs] == ["phone-a", "phone-b"]
    first_downlink = next(
        step for step in controller.created_runs[0][1][0]["steps"] if step["action"] == "traffic_server_downlink_start"
    )
    second_downlink = next(
        step for step in controller.created_runs[1][1][0]["steps"] if step["action"] == "traffic_server_downlink_start"
    )
    assert "-c 10.6.251.27" in first_downlink["params"]["command"]
    assert "-c 10.6.251.28" in second_downlink["params"]["command"]
    assert window.state.selected_run_id == "run-2"
    window.close()


def test_home_explains_single_and_dual_phone_selection_modes():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings())
    controller.refresh_devices = lambda: ["phone-a", "phone-b"]
    window = MainWindow(controller=controller, start_polling=False)

    assert "单手机" in window.home_page.run_mode_hint.text()
    assert "双手机" in window.home_page.run_mode_hint.text()
    assert "Ctrl" in window.home_page.device_selection_hint.text()

    window.home_page.run_mode_combo.setCurrentIndex(1)

    assert "至少选择两台设备" in window.home_page.device_selection_hint.text()
    window.close()


def test_home_single_phone_mode_runs_current_device_when_multiple_are_selected():
    QApplication.instance() or QApplication([])
    settings = _settings(target="")
    settings["traffic"].update(
        {
            "device_overrides": {
                "phone-a": {"server_downlink_target": "10.6.251.27"},
                "phone-b": {"server_downlink_target": "10.6.251.28"},
            }
        }
    )
    controller = FakeController(settings)
    controller.refresh_devices = lambda: ["phone-a", "phone-b"]
    window = MainWindow(controller=controller, start_polling=False)
    window.home_page.run_mode_combo.setCurrentIndex(0)
    window.home_page.device_list.item(0).setSelected(True)
    window.home_page.device_list.item(1).setSelected(True)
    window.home_page.device_list.setCurrentRow(1)

    window.home_page.start_run()

    assert [item[0] for item in controller.created_runs] == ["phone-b"]
    window.close()


def test_home_single_phone_mode_uses_single_selection_only():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings())
    controller.refresh_devices = lambda: ["phone-a", "phone-b"]
    window = MainWindow(controller=controller, start_polling=False)

    assert window.home_page.device_list.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection

    window.home_page.run_mode_combo.setCurrentIndex(1)
    assert window.home_page.device_list.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection

    window.home_page.run_mode_combo.setCurrentIndex(0)
    assert window.home_page.device_list.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection
    window.close()


def test_home_device_mapping_applies_ping_parameters_to_payload():
    QApplication.instance() or QApplication([])
    settings = _settings(target="")
    settings["traffic"].update(
        {
            "server_host": "192.168.13.164",
            "server_password": "traffic-pass",
            "device_overrides": {
                "device-1": {
                    "phone_ip": "10.6.251.27",
                    "server_ping_target": "10.6.251.27",
                    "phone_ping_target": "192.168.13.164",
                    "server_ping_count": 0,
                }
            },
        }
    )
    case = SavedCase.new(
        "ping case",
        [
            CaseStep.new("traffic_server_down_ping_start", "server ping", {}),
            CaseStep.new("phone_ping", "phone ping", {}),
        ],
    )
    controller = FakeController(settings)
    controller.get_templates = lambda: [case.to_dict()]
    window = MainWindow(controller=controller, start_polling=False)

    window.home_page.start_run()

    payload = controller.created[1][0]
    server_ping = next(step for step in payload["steps"] if step["action"] == "traffic_server_down_ping_start")
    phone_ping = next(step for step in payload["steps"] if step["action"] == "phone_ping")
    assert server_ping["params"]["ping_target"] == "10.6.251.27"
    assert server_ping["params"]["ping_count"] == 0
    assert phone_ping["params"]["server_host"] == "192.168.13.164"
    assert phone_ping["params"]["ping_count"] == 0
    window.close()


def test_home_poll_renders_selected_run_detail_to_live_log():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings())
    controller.run_detail = {
        "run_id": "run-1",
        "device_id": "device-1",
        "status": "running",
        "summary": {"passed": 0, "total": 1},
        "case_records": [
            {
                "name": "case",
                "step_records": [
                    {
                        "step_id": "ssh-1",
                        "kind": "base_ssh_command_once",
                        "status": "passed",
                        "data": {"command": "odi show", "stdout": "ok output"},
                    }
                ],
            }
        ],
    }
    window = MainWindow(controller=controller, start_polling=False)
    window.state.selected_run_id = "run-1"

    window.refresh_runs()

    text = window.home_page.live_output.toPlainText()
    assert "odi show" in text
    assert "ok output" in text
    window.close()


def test_home_live_log_stays_at_bottom_when_following_output():
    QApplication.instance() or QApplication([])
    controller = FakeController(_settings())
    window = MainWindow(controller=controller, start_polling=False)
    output = "\n".join(f"line {index}" for index in range(120))
    controller.run_detail = {
        "run_id": "run-1",
        "device_id": "device-1",
        "status": "running",
        "summary": {"passed": 0, "total": 1},
        "case_records": [
            {
                "name": "case",
                "step_records": [
                    {
                        "step_id": "ssh-1",
                        "kind": "base_ssh_command_once",
                        "status": "running",
                        "data": {"command": "odi show", "stdout": output},
                    }
                ],
            }
        ],
    }
    window.state.selected_run_id = "run-1"
    window.refresh_runs()
    bar = window.home_page.live_output.verticalScrollBar()
    bar.setValue(bar.maximum())

    controller.run_detail["case_records"][0]["step_records"][0]["data"]["stdout"] = output + "\nnew tail"
    window.refresh_runs()

    assert bar.value() == bar.maximum()
    window.close()

