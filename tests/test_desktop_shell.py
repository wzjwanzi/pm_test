import os
from pathlib import Path
import tkinter as tk

from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase
from desktop.controller import DesktopController
from desktop.main import DesktopApp
from desktop.widgets.settings import SettingsPanel


class FakeDeviceManager:
    last_error = ""

    def get_connected_devices(self):
        return ["device-1"]


class MultiDeviceManager:
    last_error = ""

    def get_connected_devices(self):
        return ["device-1", "device-2"]


class FakePmManager:
    def __init__(self):
        self.created = None
        self.created_runs = []

    def get_templates(self):
        return [{"template_id": "fixed_ping_only", "name": "Ping", "host": "1.1.1.1"}]

    def inspect_device(self, device_id):
        return {"success": True, "device_id": device_id}

    def create_run(self, device_id, cases):
        self.created = (device_id, cases)
        self.created_runs.append((device_id, cases))
        run_id = f"run-{len(self.created_runs)}"
        return {"success": True, "run": {"run_id": run_id, "device_id": device_id, "status": "queued", "summary": {"passed": 0, "total": 1}}}

    def list_runs(self, limit=20):
        return [{"run_id": "run-1", "device_id": "device-1", "status": "queued", "summary": {"passed": 0, "total": 1}}]

    def get_run(self, run_id):
        return {"run_id": run_id, "device_id": "device-1", "status": "passed", "summary": {"passed": 1, "total": 1}, "case_records": []}

    def request_stop(self, run_id):
        return {"run_id": run_id, "status": "stopping"}


def _prepare_tk_env():
    project_root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("TCL_LIBRARY", str(project_root / "release" / "MobileTestPlatform" / "_internal" / "_tcl_data"))
    os.environ.setdefault("TK_LIBRARY", str(project_root / "release" / "MobileTestPlatform" / "_internal" / "_tk_data"))


def _build_app(tmp_path=None):
    _prepare_tk_env()
    root = tk.Tk()
    root.withdraw()
    controller_kwargs = {
        "device_manager": FakeDeviceManager(),
        "pm_manager": FakePmManager(),
    }
    if tmp_path is not None:
        controller_kwargs["case_library"] = CaseLibrary(tmp_path)
    controller = DesktopController(**controller_kwargs)
    app = DesktopApp(root, controller=controller, start_polling=False)
    root.update_idletasks()
    return root, app, controller


def _build_multi_device_app(tmp_path=None):
    _prepare_tk_env()
    root = tk.Tk()
    root.withdraw()
    controller_kwargs = {
        "device_manager": MultiDeviceManager(),
        "pm_manager": FakePmManager(),
    }
    if tmp_path is not None:
        controller_kwargs["case_library"] = CaseLibrary(tmp_path)
    controller = DesktopController(**controller_kwargs)
    app = DesktopApp(root, controller=controller, start_polling=False)
    root.update_idletasks()
    return root, app, controller


def test_desktop_shell_creates_critical_panels():
    root, app, _controller = _build_app()

    assert hasattr(app, "toolbar")
    assert hasattr(app, "workbench")
    assert hasattr(app, "left_pane")
    assert hasattr(app, "center_pane")
    assert hasattr(app, "right_pane")
    assert hasattr(app, "devices_panel")
    assert hasattr(app, "cases_panel")
    assert hasattr(app, "run_monitor_panel")
    assert hasattr(app, "results_panel")
    assert hasattr(app, "settings_panel")
    assert hasattr(app, "inspector_panel")
    assert app.state.case_queue == []

    root.destroy()


def test_desktop_shell_uses_reference_workbench_layout():
    root, app, _controller = _build_app()

    assert int(app.cases_panel.grid_info()["row"]) < int(app.devices_panel.grid_info()["row"])
    assert int(app.results_panel.grid_info()["row"]) < int(app.run_monitor_panel.grid_info()["row"])
    assert app.inspector_panel.grid_info()
    assert not app.settings_panel.grid_info()

    root.destroy()


def test_poll_refreshes_selected_run_detail_for_realtime_log(monkeypatch):
    root, app, _controller = _build_app()
    calls = []
    app.state.selected_run_id = "run-1"
    app.load_run_detail = lambda run_id: calls.append(("detail", run_id))
    app.refresh_runs = lambda: calls.append(("runs", ""))
    monkeypatch.setattr(app.root, "after", lambda *_args, **_kwargs: None)

    app._schedule_poll()

    assert calls == [("detail", "run-1"), ("runs", "")]
    root.destroy()


def test_results_panel_preserves_scroll_position_on_refresh():
    root, app, _controller = _build_app()
    long_run = {
        "run_id": "run-1",
        "status": "running",
        "case_records": [
            {
                "name": "case",
                "step_records": [
                    {
                        "step_id": f"s{i}",
                        "kind": "base_ssh_command_once",
                        "adapter": "ssh",
                        "status": "passed",
                        "message": f"line {i}",
                        "data": {"command": f"cmd-{i}", "stdout": "output"},
                    }
                    for i in range(80)
                ],
            }
        ],
    }

    app.results_panel.render_run(long_run)
    app.results_panel.summary_text.yview_moveto(0.75)
    app.results_panel.raw_text.yview_moveto(0.5)
    before_summary = app.results_panel.summary_text.yview()[0]
    before_raw = app.results_panel.raw_text.yview()[0]

    app.results_panel.render_run(long_run)
    root.update_idletasks()

    assert app.results_panel.summary_text.yview()[0] >= before_summary - 0.05
    assert app.results_panel.raw_text.yview()[0] >= before_raw - 0.05
    root.destroy()


def test_results_panel_skips_rewrite_when_run_text_is_unchanged(monkeypatch):
    root, app, _controller = _build_app()
    run = {
        "run_id": "run-1",
        "status": "running",
        "case_records": [
            {"name": "case", "step_records": [{"step_id": "s1", "kind": "x", "status": "passed"}]}
        ],
    }
    app.results_panel.render_run(run)
    calls = []
    original_delete = app.results_panel.summary_text.delete

    def recording_delete(*args):
        calls.append(args)
        return original_delete(*args)

    monkeypatch.setattr(app.results_panel.summary_text, "delete", recording_delete)

    app.results_panel.render_run(run)

    assert calls == []
    root.destroy()


def test_cases_panel_has_scrollable_case_library_and_step_builder():
    root, app, _controller = _build_app()

    panel = app.cases_panel
    assert hasattr(panel, "case_list")
    assert hasattr(panel, "template_combo")
    assert hasattr(panel, "step_list")
    assert hasattr(panel, "step_params_frame")
    assert hasattr(panel, "scroll_canvas")
    assert not hasattr(panel, "queue_list")
    assert hasattr(app.devices_panel, "queue_list")
    assert "RRC 测试用例" in panel.template_combo["values"]
    assert "基站 Web" in panel.available_group_names()
    assert "基站 SSH" in panel.available_group_names()
    assert "灌包服务器" in panel.available_group_names()
    assert "手机" in panel.available_group_names()
    assert panel.case_list.bind("<MouseWheel>") == ""
    assert panel.scroll_canvas.bind("<MouseWheel>") == ""

    root.destroy()


def test_cases_panel_creates_case_from_selected_template(tmp_path):
    root, app, _controller = _build_app(tmp_path)
    panel = app.cases_panel

    panel.template_var.set("RRC 测试用例")
    panel.create_case_from_template()

    assert panel.selected_case is not None
    assert panel.selected_case.name == "RRC 测试用例"
    assert [step.action for step in panel.selected_case.steps[:4]] == [
        "base_web_capture_start",
        "base_ssh_command_start",
        "base_ssh_command_start",
        "base_ssh_command_start",
    ]

    root.destroy()


def test_desktop_shell_loads_saved_cases_on_startup(tmp_path):
    library = CaseLibrary(tmp_path)
    saved = library.save_case if hasattr(library, "save_case") else library.save
    saved(SavedCase.new("saved-on-disk", []))

    root, app, _controller = _build_app(tmp_path)

    assert app.cases_panel.case_list.size() == 1
    assert app.cases_panel.selected_case is not None
    assert app.cases_panel.selected_case.name == "saved-on-disk"

    root.destroy()


def test_start_run_uses_selected_case_when_queue_is_empty(tmp_path):
    root, app, controller = _build_app(tmp_path)
    panel = app.cases_panel
    panel.template_var.set("RRC 测试用例")
    panel.create_case_from_template()

    assert app.state.case_queue == []

    app.start_run()

    assert controller.pm_manager.created is not None
    assert controller.pm_manager.created[0] == "device-1"
    assert controller.pm_manager.created[1][0]["name"] == "RRC 测试用例"
    assert app.state.case_queue == [panel.selected_case]

    root.destroy()


def test_start_run_remaps_saved_case_params_from_current_settings(tmp_path):
    root, app, controller = _build_app(tmp_path)
    case = controller.create_case_from_template("RRC 测试用例", {"ssh": {"host": "10.88.149.164", "password": ""}})
    app.state.add_case(case)
    app.cases_panel.refresh_queue()

    controller.save_settings(
        {
            "ssh": {"host": "192.168.13.236", "port": 22, "username": "root", "password": "Root@236_"},
            "traffic": {"server_ping_target": "10.6.250.2"},
            "base_web": {"host": "192.168.13.236", "port": 8400, "capture_fapi_interface": "FAPI1"},
        }
    )

    app.start_run()

    payload = controller.pm_manager.created[1][0]
    ssh_step = next(step for step in payload["steps"] if step["action"] == "base_ssh_command_start")
    ping_step = next(step for step in payload["steps"] if step["action"] == "traffic_server_down_ping_start")
    assert ssh_step["params"]["ssh_host"] == "192.168.13.236"
    assert ssh_step["params"]["ssh_password"] == "Root@236_"
    assert ping_step["params"]["ping_target"] == "10.6.250.2"

    root.destroy()


def test_start_run_preserves_per_step_delay_seconds(tmp_path):
    root, app, controller = _build_app(tmp_path)
    case = controller.create_case_from_template("下行灌包", {"common": {"delay_seconds": 5}})
    delay_step = next(step for step in case.steps if step.action == "common_delay")
    delay_step.params["delay_seconds"] = "90"
    controller.save_case(case)
    app.state.add_case(case)
    app.cases_panel.refresh_queue()

    app.start_run()

    payload = controller.pm_manager.created[1][0]
    delay_payload = next(step for step in payload["steps"] if step["action"] == "common_delay")
    assert delay_payload["params"]["delay_seconds"] == "90"

    root.destroy()


def test_start_run_can_run_same_queue_on_two_selected_devices(tmp_path):
    root, app, controller = _build_multi_device_app(tmp_path)
    case = SavedCase.new("case-a", [])
    controller.save_case(case)
    app.state.add_case(case)
    app.devices_panel.device_list.selection_clear(0, tk.END)
    app.devices_panel.device_list.selection_set(0)
    app.devices_panel.device_list.selection_set(1)
    app.devices_panel._on_select()
    app.devices_panel.run_mode_var.set(app.devices_panel.RUN_MODE_SAME)

    app.start_run()

    assert [device for device, _cases in controller.pm_manager.created_runs] == ["device-1", "device-2"]
    assert all(cases[0]["name"] == case.name for _device, cases in controller.pm_manager.created_runs)
    assert app.state.selected_run_ids == ["run-1", "run-2"]
    assert app.state.selected_run_id == "run-2"

    root.destroy()


def test_start_run_applies_per_device_traffic_overrides_and_discards_stale_commands(tmp_path):
    root, app, controller = _build_multi_device_app(tmp_path)
    case = SavedCase.new(
        "dual-traffic",
        [
            CaseStep.new(
                "phone_downlink_receive_start",
                "phone downlink",
                {"phone_downlink_listen_port": 6011, "arguments": "-u -s -i 1 -p 9999"},
            ),
            CaseStep.new(
                "traffic_server_downlink_start",
                "server downlink",
                {
                    "server_downlink_target": "10.6.251.1",
                    "server_downlink_port": 6011,
                    "command": "iperf -u -c 10.6.251.1 -p 9999",
                },
            ),
            CaseStep.new(
                "traffic_server_uplink_receive_start",
                "server uplink receive",
                {"server_uplink_listen_port": 7011, "command": "iperf -u -s -p 9999"},
            ),
            CaseStep.new(
                "phone_uplink_iperf_start",
                "phone uplink",
                {
                    "phone_uplink_target": "10.88.149.164",
                    "phone_uplink_port": 7011,
                    "arguments": "-u -c 10.88.149.164 -p 9999",
                },
            ),
            CaseStep.new(
                "traffic_server_down_ping_start",
                "server ping",
                {"ping_target": "10.6.251.1", "command": "ping 10.6.251.1 -n 5"},
            ),
        ],
    )
    controller.save_case(case)
    app.state.add_case(case)
    app.devices_panel.device_list.selection_clear(0, tk.END)
    app.devices_panel.device_list.selection_set(0)
    app.devices_panel.device_list.selection_set(1)
    app.devices_panel._on_select()
    app.devices_panel.run_mode_var.set(app.devices_panel.RUN_MODE_SAME)
    controller.save_settings(
        {
            "traffic": {
                "server_host": "10.88.149.164",
                "device_overrides": {
                    "device-1": {"phone_ip": "10.6.251.27", "downlink_port": 6011, "uplink_port": 7011},
                    "device-2": {"phone_ip": "10.6.251.28", "downlink_port": 6012, "uplink_port": 7012},
                },
            }
        }
    )

    app.start_run()

    first_payload = controller.pm_manager.created_runs[0][1][0]
    second_payload = controller.pm_manager.created_runs[1][1][0]
    assert controller.pm_manager.created_runs[0][0] == "device-1"
    assert controller.pm_manager.created_runs[1][0] == "device-2"
    first_params = {step["action"]: step["params"] for step in first_payload["steps"]}
    second_params = {step["action"]: step["params"] for step in second_payload["steps"]}
    assert first_params["traffic_server_downlink_start"]["server_downlink_target"] == "10.6.251.27"
    assert first_params["phone_downlink_receive_start"]["phone_downlink_listen_port"] == 6011
    assert second_params["traffic_server_downlink_start"]["server_downlink_target"] == "10.6.251.28"
    assert second_params["traffic_server_downlink_start"]["server_downlink_port"] == 6012
    assert second_params["phone_downlink_receive_start"]["phone_downlink_listen_port"] == 6012
    assert second_params["traffic_server_uplink_receive_start"]["server_uplink_listen_port"] == 7012
    assert second_params["phone_uplink_iperf_start"]["phone_uplink_port"] == 7012
    assert second_params["phone_uplink_iperf_start"]["phone_uplink_target"] == "10.88.149.164"
    assert second_params["traffic_server_down_ping_start"]["ping_target"] == "10.6.251.28"
    assert "command" not in second_params["traffic_server_downlink_start"]
    assert "command" not in second_params["traffic_server_uplink_receive_start"]
    assert "arguments" not in second_params["phone_uplink_iperf_start"]
    assert "arguments" not in second_params["phone_downlink_receive_start"]

    root.destroy()


def test_start_run_can_run_different_cases_on_different_devices(tmp_path):
    root, app, controller = _build_multi_device_app(tmp_path)
    case_a = SavedCase.new("case-a", [])
    case_b = SavedCase.new("case-b", [])
    controller.save_case(case_a)
    controller.save_case(case_b)
    app.state.add_case(case_a)
    app.state.add_case(case_b)
    app.state.assign_case_devices(0, ["device-1"])
    app.state.assign_case_devices(1, ["device-2"])
    app.devices_panel.run_mode_var.set(app.devices_panel.RUN_MODE_BY_CASE)

    app.start_run()

    assert [device for device, _cases in controller.pm_manager.created_runs] == ["device-1", "device-2"]
    assert controller.pm_manager.created_runs[0][1][0]["name"] == case_a.name
    assert controller.pm_manager.created_runs[1][1][0]["name"] == case_b.name

    root.destroy()


def test_cases_panel_edits_steps_params_queue_and_run(tmp_path):
    controller = DesktopController(
        device_manager=FakeDeviceManager(),
        pm_manager=FakePmManager(),
        case_library=CaseLibrary(tmp_path),
    )
    controller.create_case_from_template("下行灌包", {"traffic_server_host": "10.88.149.164"})
    _prepare_tk_env()
    root = tk.Tk()
    root.withdraw()
    app = DesktopApp(root, controller=controller, start_polling=False)
    root.update_idletasks()
    panel = app.cases_panel

    assert panel.case_list.size() == 1
    assert panel.selected_case is not None
    assert panel.selected_case.steps[0].action == "base_web_capture_start"

    panel.step_list.selection_clear(0, tk.END)
    panel.step_list.selection_set(0)
    panel._on_step_select()
    assert "capture_signal_enabled" in panel._param_vars
    assert "capture_data_enabled" in panel._param_vars
    assert "capture_fapi_interface" in panel._param_vars
    panel._param_vars["capture_fapi_interface"].set("FAPI3")
    panel.toggle_step_enabled()
    assert panel.selected_case.steps[0].params["capture_fapi_interface"] == "FAPI3"
    assert panel.selected_case.steps[0].enabled is False
    panel.toggle_step_enabled()
    assert panel.selected_case.steps[0].enabled is True

    original_count = len(panel.selected_case.steps)
    panel.add_step("phone_ping")
    assert len(panel.selected_case.steps) == original_count + 1
    last_index = len(panel.selected_case.steps) - 1
    panel.step_list.selection_clear(0, tk.END)
    panel.step_list.selection_set(last_index)
    panel.move_step_up()
    assert panel.selected_case.steps[last_index - 1].action == "phone_ping"
    panel.move_step_down()
    assert panel.selected_case.steps[last_index].action == "phone_ping"
    panel.toggle_step_enabled()
    assert panel.selected_case.steps[last_index].enabled is False
    panel.delete_selected_step()
    assert len(panel.selected_case.steps) == original_count

    panel.add_selected_case_to_queue()
    assert app.state.case_queue == [panel.selected_case]
    queue_text = app.devices_panel.queue_list.get(0)
    assert panel.selected_case.name in queue_text
    assert str(len(panel.selected_case.steps)) in queue_text

    app.set_selected_device("device-1")
    app.start_run()

    assert controller.pm_manager.created[0] == "device-1"
    assert controller.pm_manager.created[1][0]["steps"][0]["action"] == "base_web_capture_start"

    root.destroy()


def test_cases_panel_saves_selected_step_params_independently(tmp_path):
    root, app, controller = _build_app(tmp_path)
    panel = app.cases_panel
    panel.template_var.set("下行灌包")
    panel.create_case_from_template()

    assert panel.selected_case is not None
    first_delay_index = next(
        index for index, step in enumerate(panel.selected_case.steps) if step.action == "common_delay"
    )
    panel.add_step("common_delay")
    second_delay_index = len(panel.selected_case.steps) - 1

    panel.step_list.selection_clear(0, tk.END)
    panel.step_list.selection_set(first_delay_index)
    panel._on_step_select()
    panel._param_vars["delay_seconds"].set("20")
    panel.save_current_step_params()

    saved_case = controller.case_library.load(panel.selected_case.case_id)
    assert saved_case.steps[first_delay_index].params["delay_seconds"] == "20"
    assert saved_case.steps[second_delay_index].params["delay_seconds"] == "5"
    assert hasattr(panel, "save_step_params_button")

    root.destroy()


def test_cases_panel_previews_step_parameters_when_action_catalog_clicked(tmp_path):
    root, app, _controller = _build_app(tmp_path)
    panel = app.cases_panel

    panel.selected_case = None
    panel.preview_step_template("base_web_capture_start")

    assert panel._param_step_id == ""
    assert "web_host" in panel._param_vars
    assert "capture_fapi_interface" in panel._param_vars

    panel.preview_step_template("phone_ping")

    assert "server_host" in panel._param_vars
    assert "ping_count" in panel._param_vars
    assert "web_host" not in panel._param_vars

    root.destroy()


def test_inspector_groups_base_station_and_traffic_parameters(tmp_path):
    controller = DesktopController(
        device_manager=FakeDeviceManager(),
        pm_manager=FakePmManager(),
        case_library=CaseLibrary(tmp_path),
    )
    case = controller.create_case_from_template("下行灌包", {"traffic_server_host": "10.88.149.164"})
    _prepare_tk_env()
    root = tk.Tk()
    root.withdraw()
    app = DesktopApp(root, controller=controller, start_polling=False)
    root.update_idletasks()

    app.inspector_panel.render_case(case)
    rows = [
        app.inspector_panel.parameter_table.item(item, "values")
        for item in app.inspector_panel.parameter_table.get_children()
    ]
    base_rows = [row for row in rows if row[0] == "基站"]
    traffic_rows = [row for row in rows if row[0] == "灌包"]

    assert base_rows
    assert traffic_rows
    assert all(row[1] not in {"iperf_port", "iperf_bandwidth", "iperf_duration"} for row in base_rows)
    assert any(row[1] == "iperf_bandwidth" for row in traffic_rows)

    root.destroy()


def test_settings_panel_saves_each_group_independently():
    class FakeController:
        def __init__(self):
            self.settings = {
                "base_web": {
                    "host": "192.168.13.236",
                    "port": 8400,
                    "username": "root",
                    "password": "web-pass",
                    "log_download_dir": r"D:\web_logs",
                    "capture_signal_enabled": True,
                    "capture_data_enabled": False,
                    "capture_fapi_interface": "FAPI1",
                },
                "ssh": {"host": "10.88.149.164", "port": 22},
                "traffic": {"server_host": "10.88.149.164", "server_password": "traffic-pass"},
                "iperf": {"host": "10.88.149.164", "port": 6087},
                "ping": {"host": "10.88.149.164", "count": 5},
            }
            self.saved = []

        def load_settings(self):
            return self.settings

        def save_settings(self, settings):
            self.saved.append(settings)
            self.settings = settings
            return settings

        def reset_settings(self):
            return self.settings

    class FakeApp:
        def __init__(self):
            self.controller = FakeController()
            self.messages = []

        def set_message(self, text):
            self.messages.append(text)

    _prepare_tk_env()
    root = tk.Tk()
    root.withdraw()
    app = FakeApp()
    panel = SettingsPanel(root, app)
    panel.grid(row=0, column=0, sticky="nsew")
    root.update_idletasks()
    panel.load()
    assert panel.save_current_button.grid_info()
    panel.field_vars["base_web"]["host"].set("192.168.13.250")
    panel.field_vars["base_web"]["password"].set("new-web")

    panel.save_current_group()

    assert len(app.controller.saved) == 1
    assert app.controller.settings["base_web"]["host"] == "192.168.13.250"
    assert app.controller.settings["base_web"]["password"] == "new-web"
    assert app.controller.settings["traffic"]["server_host"] == "10.88.149.164"
    assert app.messages

    root.destroy()


def test_toolbar_open_config_creates_settings_window():
    root, app, _controller = _build_app()

    app.open_settings_window()
    root.update_idletasks()

    assert hasattr(app, "settings_window")
    assert app.settings_window.winfo_exists()
    assert hasattr(app, "active_settings_panel")
    assert app.active_settings_panel.field_vars["base_web"]["host"].get()
    assert app.active_settings_panel.field_vars["ssh"]["host"].get()

    app.settings_window.destroy()
    root.destroy()
