from desktop.case_models import CaseStep, SavedCase
from desktop_qt.preflight import Severity, evaluate_case_readiness


def test_single_mode_shows_selected_device_mapping_details():
    case = SavedCase.new("downlink", [CaseStep.new("traffic_server_downlink_start", "downlink", {})])
    settings = {
        "traffic": {
            "server_host": "192.168.13.164",
            "server_password": "traffic-pass",
            "server_downlink_target": "10.6.251.27",
            "device_overrides": {
                "device-1": {"phone_ip": "10.6.251.27", "downlink_port": 6011, "uplink_port": 7011}
            },
        }
    }

    result = evaluate_case_readiness(case, settings, ["device-1"], {"adb_ok": True}, run_mode="single")

    mapping_items = [item for group in result.groups for item in group.items if item.label == "device-1"]
    assert mapping_items
    assert mapping_items[0].severity == Severity.OK
    assert "10.6.251.27" in mapping_items[0].message
    assert "6011" in mapping_items[0].message
    assert "7011" in mapping_items[0].message
