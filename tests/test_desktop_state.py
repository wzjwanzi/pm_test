from desktop.state import CaseDraft, DesktopState, normalize_status


def test_case_draft_converts_to_legacy_case_dict():
    case = CaseDraft(
        name="Ping Case",
        host="10.0.0.1",
        capture_enabled=True,
        ping_enabled=True,
        server_action="base_ssh_output_log",
    )

    assert case.to_legacy_case() == {
        "name": "Ping Case",
        "host": "10.0.0.1",
        "count": 5,
        "capture_enabled": True,
        "ping_enabled": True,
        "server_action": "base_ssh_output_log",
    }


def test_desktop_state_manages_case_queue_and_selection():
    state = DesktopState()
    state.add_case(CaseDraft(name="A", host="1.1.1.1"))
    state.add_case(CaseDraft(name="B", host="2.2.2.2"))

    assert state.selected_case_index == 1
    assert state.selected_case().name == "B"

    state.select_case(0)
    assert state.selected_case().name == "A"

    state.clear_cases()
    assert state.selected_case() is None
    assert state.selected_case_index == -1


def test_normalize_status_prefers_status_then_state():
    assert normalize_status({"status": "passed", "state": "failed"}) == "passed"
    assert normalize_status({"state": "running"}) == "running"
    assert normalize_status({}) == "queued"
