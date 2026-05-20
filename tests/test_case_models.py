from desktop.case_models import CaseStep, SavedCase, validate_case


def test_saved_case_round_trips_schema_v1():
    case = SavedCase.new(
        name="test1",
        steps=[
            CaseStep.new(
                action="base_web_capture_start",
                label="基站 Web-开始抓包",
                params={
                    "capture_signal_enabled": True,
                    "capture_data_enabled": False,
                    "capture_fapi_interface": "FAPI1",
                },
            )
        ],
    )

    data = case.to_dict()
    loaded = SavedCase.from_dict(data)

    assert data["schema_version"] == 1
    assert loaded.name == "test1"
    assert loaded.steps[0].action == "base_web_capture_start"
    assert loaded.steps[0].enabled is True


def test_validate_case_requires_name_and_enabled_step():
    empty_name = SavedCase.new(name=" ", steps=[CaseStep.new("phone_ping", "手机-ping", {})])
    no_enabled_steps = SavedCase.new(
        name="test1",
        steps=[CaseStep.new("phone_ping", "手机-ping", {}, enabled=False)],
    )

    assert "用例名称不能为空" in validate_case(empty_name).errors
    assert "至少需要一个启用步骤" in validate_case(no_enabled_steps).errors
