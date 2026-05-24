"""Controller layer for the Tkinter desktop application."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app_settings import (
    export_runtime_settings,
    import_runtime_settings,
    load_runtime_settings,
    reset_runtime_settings,
    save_runtime_settings,
    save_runtime_settings_group,
)
from desktop.artifacts import export_run_report, open_artifact_dir
from desktop.case_library import CaseLibrary
from desktop.case_models import CaseStep, SavedCase
from desktop.case_operations import case_to_run_payload as resolve_case_to_run_payload
from desktop.case_templates import ACTIONS, build_default_case_templates
from device import DeviceManager
from pm_tests import PmTestRunManager
from pm_tests.base_station_config import BaseStationConfigClient


class DesktopController:
    """Thin facade used by desktop widgets."""

    def __init__(
        self,
        *,
        device_manager: Any | None = None,
        pm_manager: Any | None = None,
        case_library: CaseLibrary | None = None,
    ):
        self.device_manager = device_manager or DeviceManager()
        self.pm_manager = pm_manager or PmTestRunManager()
        self.case_library = case_library or CaseLibrary()

    def refresh_devices(self) -> list[str]:
        return list(self.device_manager.get_connected_devices())

    def inspect_device(self, device_id: str) -> dict:
        return self.pm_manager.inspect_device(device_id)

    def get_templates(self) -> list[dict]:
        saved_cases = self.case_library.list_cases()
        settings = self.load_settings()
        default_cases = build_default_case_templates(settings)
        default_by_name = {case.name: case for case in default_cases}
        templates = []
        existing_names = set()
        for case in saved_cases:
            if case.name in default_by_name:
                case = _merge_saved_builtin_case(case, default_by_name[case.name])
                self.case_library.save(case)
            templates.append(case.to_dict())
            existing_names.add(case.name)
        for case in default_cases:
            if case.name not in existing_names:
                templates.append(case.to_dict())
        if templates:
            return templates
        return list(self.pm_manager.get_templates())

    def create_run(self, device_id: str, cases) -> dict:
        run_cases = [self.case_to_run_payload(item) for item in cases]
        return self.pm_manager.create_run(device_id, run_cases)

    def list_saved_cases(self):
        return self.case_library.list_cases()

    def create_blank_case(self, name: str, settings: dict) -> SavedCase:
        case = SavedCase.new(name, [])
        self.case_library.save(case)
        return case

    def create_case_from_template(self, template_name: str, settings: dict) -> SavedCase:
        for case in self.case_library.list_cases():
            if case.name == template_name:
                return self.case_library.copy_case(case.case_id, case.name)
        for case in build_default_case_templates(settings):
            if case.name == template_name:
                self.case_library.save(case)
                return case
        raise ValueError(f"Unknown case template: {template_name}")

    def save_case(self, case):
        case = self._upgrade_builtin_case_if_needed(case)
        self.case_library.save(case)
        return case

    def rename_case(self, case_id: str, name: str):
        return self.case_library.rename(case_id, name)

    def copy_case(self, case_id: str, name: str):
        return self.case_library.copy_case(case_id, name)

    def delete_case(self, case_id: str):
        return self.case_library.delete(case_id)

    def get_step_templates(self) -> list[dict]:
        return [asdict(item) for item in ACTIONS]

    def request_stop(self, run_id: str) -> dict | None:
        return self.pm_manager.request_stop(run_id)

    def get_run(self, run_id: str) -> dict | None:
        return self.pm_manager.get_run(run_id)

    def list_runs(self, limit: int = 20) -> list[dict]:
        return list(self.pm_manager.list_runs(limit=limit))

    def export_run_report(self, run: dict) -> Any:
        return export_run_report(run)

    def open_artifact_dir(self, run: dict, *, opener=None) -> Any:
        return open_artifact_dir(run, opener=opener)

    def load_settings(self) -> dict:
        return load_runtime_settings()

    def discover_base_station_nodes(self) -> list[dict[str, str]]:
        client = BaseStationConfigClient(self.load_settings().get("base_web") or {})
        return [dict(path=node.path, label=node.label) for node in client.discover_nodes()]

    def get_base_station_node_parameters(self, node: str) -> dict[str, str]:
        client = BaseStationConfigClient(self.load_settings().get("base_web") or {})
        return client.get_node_parameters(node)

    def get_base_station_common_parameters(self, node: str) -> dict[str, str]:
        client = BaseStationConfigClient(self.load_settings().get("base_web") or {})
        return client.get_common_parameters(node)

    def set_base_station_node_parameters(self, node: str, values: dict[str, Any]) -> dict[str, Any]:
        client = BaseStationConfigClient(self.load_settings().get("base_web") or {})
        return client.set_node_parameters(node, values)

    def set_base_station_common_parameters(self, node: str, values: dict[str, Any]) -> dict[str, Any]:
        client = BaseStationConfigClient(self.load_settings().get("base_web") or {})
        return client.set_common_parameters(node, values)

    def save_settings(self, settings: dict) -> dict:
        return save_runtime_settings(settings)

    def export_settings(self, path) -> Any:
        return export_runtime_settings(path)

    def import_settings(self, path) -> dict:
        return import_runtime_settings(path)

    def save_settings_group(self, group: str, settings: dict) -> dict:
        return save_runtime_settings_group(group, settings)

    def reset_settings(self) -> dict:
        return reset_runtime_settings()

    def case_to_run_payload(self, item) -> dict:
        if hasattr(item, "to_legacy_case"):
            return item.to_legacy_case()
        if isinstance(item, dict):
            return item
        return resolve_case_to_run_payload(item, self.load_settings())

    def _upgrade_builtin_case_if_needed(self, case: SavedCase) -> SavedCase:
        default_by_name = {item.name: item for item in build_default_case_templates(self.load_settings())}
        if case.name in default_by_name:
            return _merge_saved_builtin_case(case, default_by_name[case.name])
        return case


def _merge_saved_builtin_case(saved: SavedCase, latest: SavedCase) -> SavedCase:
    saved_by_occurrence = _steps_by_action_occurrence(saved.steps)
    merged_steps = []
    latest_counts: dict[str, int] = {}
    changed = len(saved.steps) != len(latest.steps)
    for latest_step in latest.steps:
        occurrence = latest_counts.get(latest_step.action, 0)
        latest_counts[latest_step.action] = occurrence + 1
        saved_step = saved_by_occurrence.get((latest_step.action, occurrence))
        if saved_step is None:
            merged_steps.append(latest_step)
            changed = True
            continue
        merged_step = CaseStep.from_dict(latest_step.to_dict())
        merged_step.step_id = saved_step.step_id
        merged_step.enabled = saved_step.enabled
        merged_step.required = saved_step.required
        merged_step.params.update(saved_step.params)
        merged_step.param_overrides = dict(saved_step.param_overrides)
        merged_steps.append(merged_step)
    saved_actions = [step.action for step in saved.steps]
    merged_actions = [step.action for step in merged_steps]
    if saved_actions != merged_actions:
        changed = True
    if changed:
        saved.steps = merged_steps
    return saved


def _steps_by_action_occurrence(steps) -> dict[tuple[str, int], CaseStep]:
    counts: dict[str, int] = {}
    indexed = {}
    for step in steps:
        occurrence = counts.get(step.action, 0)
        counts[step.action] = occurrence + 1
        indexed[(step.action, occurrence)] = step
    return indexed
