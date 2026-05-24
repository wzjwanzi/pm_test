from desktop.case_models import CaseStep, SavedCase
from desktop_qt.preflight import Severity, evaluate_case_readiness


def test_phone_group_shows_selected_device_ids():
    case = SavedCase.new("downlink", [CaseStep.new("traffic_server_downlink_start", "downlink", {})])
    settings = {
        "traffic": {
            "server_host": "192.168.13.164",
            "server_password": "traffic-pass",
            "server_downlink_target": "10.6.251.27",
        }
    }

    result = evaluate_case_readiness(case, settings, ["MKBUT20605024486"], {"adb_ok": True})

    selected_items = [item for group in result.groups for item in group.items if "MKBUT20605024486" in item.message]
    assert selected_items
    assert selected_items[0].severity == Severity.OK
    assert "MKBUT20605024486" in selected_items[0].message
