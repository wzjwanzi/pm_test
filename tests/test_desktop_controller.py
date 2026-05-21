from desktop.controller import DesktopController
from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase
from desktop.state import CaseDraft
import config


class FakeDeviceManager:
    last_error = ""

    def get_connected_devices(self):
        return ["device-1"]


class FakePmManager:
    def __init__(self):
        self.created = None

    def get_templates(self):
        return [{"template_id": "fixed_ping_only", "name": "Ping", "host": "1.1.1.1"}]

    def inspect_device(self, device_id):
        return {"success": True, "device_id": device_id}

    def create_run(self, device_id, cases):
        self.created = (device_id, cases)
        return {"success": True, "run": {"run_id": "run-1", "device_id": device_id, "status": "queued"}}

    def list_runs(self, limit=20):
        return [{"run_id": "run-1", "status": "queued"}]

    def get_run(self, run_id):
        return {"run_id": run_id, "status": "passed"}

    def request_stop(self, run_id):
        return {"run_id": run_id, "status": "stopping"}


def test_controller_creates_run_from_case_drafts():
    pm = FakePmManager()
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=pm)

    result = controller.create_run("device-1", [CaseDraft(name="case", host="1.1.1.1")])

    assert result["run"]["run_id"] == "run-1"
    assert pm.created[0] == "device-1"
    assert pm.created[1][0]["name"] == "case"


def test_controller_exposes_case_library_operations(tmp_path):
    controller = DesktopController()
    controller.case_library.root = tmp_path

    case = controller.create_case_from_template("下行灌包", {"traffic_server_host": "10.88.149.164"})
    controller.rename_case(case.case_id, "test1")
    cases = controller.list_saved_cases()

    assert cases[0].name == "test1"
    assert cases[0].steps[0].action == "base_web_capture_start"


def test_controller_uses_saved_cases_as_templates(tmp_path):
    library = CaseLibrary(tmp_path)
    source = SavedCase.new(
        "saved-template",
        [CaseStep.new("phone_ping", "ping", {"host": "10.0.0.1", "count": 1})],
    )
    library.save(source)
    controller = DesktopController(
        device_manager=FakeDeviceManager(),
        pm_manager=FakePmManager(),
        case_library=library,
    )

    templates = controller.get_templates()
    created = controller.create_case_from_template("saved-template", {})

    assert "saved-template" in [item["name"] for item in templates]
    assert "双向灌包" in [item["name"] for item in templates]
    assert created.name == "saved-template"
    assert created.case_id != source.case_id
    assert created.steps[0].action == "phone_ping"
    assert len(controller.list_saved_cases()) == 2


def test_controller_create_run_passes_saved_case_steps_as_dicts():
    pm = FakePmManager()
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=pm)
    saved_case = SavedCase.new(
        "saved",
        [CaseStep.new("base_web_capture_start", "capture", {"capture_fapi_interface": "FAPI1"})],
    )

    result = controller.create_run("device-1", [saved_case])

    assert result["run"]["run_id"] == "run-1"
    assert pm.created[1][0]["name"] == "saved"
    assert pm.created[1][0]["steps"][0]["action"] == "base_web_capture_start"
    assert pm.created[1][0]["steps"][0]["params"]["capture_fapi_interface"] == "FAPI1"


def test_controller_create_run_passes_plain_dict_cases_as_is():
    pm = FakePmManager()
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=pm)
    case = {"name": "plain", "steps": [{"action": "phone_ping"}]}

    controller.create_run("device-1", [case])

    assert pm.created[1][0] is case


def test_controller_wraps_devices_templates_and_runs():
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=FakePmManager())

    assert controller.refresh_devices() == ["device-1"]
    template_names = [item["name"] for item in controller.get_templates()]
    assert "双向灌包" in template_names
    assert "入网" in template_names
    assert controller.inspect_device("device-1")["success"] is True
    assert controller.list_runs()[0]["run_id"] == "run-1"
    assert controller.get_run("run-1")["status"] == "passed"
    assert controller.request_stop("run-1")["status"] == "stopping"


def test_controller_exports_report_and_opens_artifacts(tmp_path):
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=FakePmManager())
    run = {
        "run_id": "run-1",
        "device_id": "device-1",
        "status": "passed",
        "artifact_dir": str(tmp_path),
        "summary": {"total": 1, "passed": 1, "failed": 0},
    }
    opened = []

    report_path = controller.export_run_report(run)
    opened_path = controller.open_artifact_dir(run, opener=lambda path: opened.append(path))

    assert report_path == tmp_path / "run_report.md"
    assert report_path.exists()
    assert opened_path == tmp_path.resolve()
    assert opened == [tmp_path.resolve()]


def test_controller_saves_one_settings_group_without_touching_others(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    controller = DesktopController(device_manager=FakeDeviceManager(), pm_manager=FakePmManager())
    settings = controller.load_settings()
    settings["traffic"]["server_host"] = "10.88.149.164"
    settings["traffic"]["server_password"] = "traffic-pass"
    controller.save_settings(settings)

    controller.save_settings_group("base_web", {"host": "192.168.13.250", "password": "web-pass"})
    reloaded = controller.load_settings()

    assert reloaded["base_web"]["host"] == "192.168.13.250"
    assert reloaded["base_web"]["password"] == "web-pass"
    assert reloaded["traffic"]["server_host"] == "10.88.149.164"
    assert reloaded["traffic"]["server_password"] == "traffic-pass"
