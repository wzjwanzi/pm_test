from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QListWidget, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from desktop.case_models import SavedCase


class CaseLibraryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cases: list[Any] = []
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.case_list = QListWidget()
        self.add_to_run_button = QPushButton("加入运行")
        left.addWidget(self.case_list)
        left.addWidget(self.add_to_run_button)

        self.step_list = QListWidget()
        self.parameter_list = QListWidget()
        layout.addLayout(left, 1)
        layout.addWidget(self.step_list, 2)
        layout.addWidget(self.parameter_list, 2)

        self.case_list.currentRowChanged.connect(self.render_selected_case)
        self.add_to_run_button.clicked.connect(self.add_selected_to_run)
        self.load_cases()

    def load_cases(self) -> None:
        self.cases = [_case_from_template(item) for item in self.window.controller.get_templates()]
        self.case_list.clear()
        for case in self.cases:
            self.case_list.addItem(str(getattr(case, "name", "") or "未命名用例"))
        if self.cases:
            self.case_list.setCurrentRow(0)

    def render_selected_case(self) -> None:
        case = self.selected_case()
        self.step_list.clear()
        self.parameter_list.clear()
        for step in getattr(case, "steps", []) if case is not None else []:
            self.step_list.addItem(f"{getattr(step, 'label', '') or getattr(step, 'action', '')}")
            for key, value in getattr(step, "params", {}).items():
                self.parameter_list.addItem(f"{key}: {value}")

    def add_selected_to_run(self) -> None:
        case = self.selected_case()
        if case is None:
            return
        self.window.state.selected_case = case
        if case not in self.window.home_page.cases:
            self.window.home_page.cases.insert(0, case)
            self.window.home_page.case_list.insertItem(0, case.name)
        self.window.home_page.case_list.setCurrentRow(self.window.home_page.cases.index(case))
        self.window.home_page.refresh_readiness()

    def selected_case(self):
        row = self.case_list.currentRow()
        if 0 <= row < len(self.cases):
            return self.cases[row]
        return None


def _case_from_template(template: Any):
    if isinstance(template, SavedCase):
        return template
    if isinstance(template, dict) and template.get("steps"):
        return SavedCase.from_dict(template)
    return template
