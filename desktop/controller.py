"""Controller layer for the Tkinter desktop application."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app_settings import (
    load_runtime_settings,
    reset_runtime_settings,
    save_runtime_settings,
    save_runtime_settings_group,
)
from desktop.artifacts import export_run_report, open_artifact_dir
from desktop.case_library import CaseLibrary
from desktop.case_models import SavedCase
from desktop.case_templates import ACTIONS, build_default_case_templates
from device import DeviceManager
from pm_tests import PmTestRunManager


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
        if saved_cases:
            return [case.to_dict() for case in saved_cases]
        return list(self.pm_manager.get_templates())

    def create_run(self, device_id: str, cases) -> dict:
        run_cases = [self._case_to_run_payload(item) for item in cases]
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

    def save_settings(self, settings: dict) -> dict:
        return save_runtime_settings(settings)

    def save_settings_group(self, group: str, settings: dict) -> dict:
        return save_runtime_settings_group(group, settings)

    def reset_settings(self) -> dict:
        return reset_runtime_settings()

    def _case_to_run_payload(self, item) -> dict:
        if hasattr(item, "to_legacy_case"):
            return item.to_legacy_case()
        if hasattr(item, "to_dict"):
            return item.to_dict()
        if isinstance(item, dict):
            return item
        return dict(item)
