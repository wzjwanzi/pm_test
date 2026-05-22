from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop.case_models import SavedCase
from desktop.formatters import format_run_console
from desktop_qt.preflight import Severity, evaluate_case_readiness


class HomePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cases: list[Any] = []
        self.devices: list[str] = []

        layout = QVBoxLayout(self)
        self.device_group = QGroupBox("当前设备")
        self.device_list = QListWidget()
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItems(["单手机", "双手机"])
        device_layout = QVBoxLayout(self.device_group)
        device_layout.addWidget(self.device_list)
        device_layout.addWidget(self.run_mode_combo)

        self.case_group = QGroupBox("选择用例")
        self.case_list = QListWidget()
        case_layout = QVBoxLayout(self.case_group)
        case_layout.addWidget(self.case_list)

        self.readiness_group = QGroupBox("配置检查")
        self.readiness_list = QListWidget()
        readiness_layout = QVBoxLayout(self.readiness_group)
        readiness_layout.addWidget(self.readiness_list)

        self.preflight_button = QPushButton("预检")
        self.start_button = QPushButton("开始测试")
        self.message_label = QLabel("")
        self.live_output = QTextEdit()
        self.live_output.setReadOnly(True)

        layout.addWidget(self.device_group)
        layout.addWidget(self.case_group)
        layout.addWidget(self.readiness_group)
        layout.addWidget(self.preflight_button)
        layout.addWidget(self.start_button)
        layout.addWidget(self.message_label)
        layout.addWidget(QLabel("实时执行"))
        layout.addWidget(self.live_output)

        self.device_list.itemSelectionChanged.connect(self._on_device_selection_changed)
        self.case_list.currentRowChanged.connect(lambda _row: self.refresh_readiness())
        self.run_mode_combo.currentIndexChanged.connect(lambda _index: self.refresh_readiness())
        self.preflight_button.clicked.connect(self.refresh_readiness)
        self.start_button.clicked.connect(self.start_run)

        self.refresh_devices()
        self.load_cases()
        self.refresh_readiness()

    def refresh_devices(self) -> None:
        self.devices = list(self.window.controller.refresh_devices())
        self.device_list.clear()
        self.device_list.addItems(self.devices)
        if self.devices:
            self.device_list.setCurrentRow(0)
            self.window.state.selected_devices = [self.devices[0]]

    def load_cases(self) -> None:
        self.cases = [_case_from_template(item) for item in self.window.controller.get_templates()]
        self.case_list.clear()
        for case in self.cases:
            self.case_list.addItem(str(getattr(case, "name", "") or "未命名用例"))
        if self.cases:
            self.case_list.setCurrentRow(0)
            self.window.state.selected_case = self.cases[0]

    def refresh_readiness(self) -> None:
        case = self.selected_case()
        if case is not None:
            self.window.state.selected_case = case
        result = self._readiness()
        self.readiness_list.clear()
        for group in result.groups:
            self.readiness_list.addItem(f"[{group.name}]")
            for item in group.items:
                prefix = _severity_text(item.severity)
                self.readiness_list.addItem(f"  {prefix} {item.label}: {item.message}")
        self.message_label.setText("；".join(result.blocking_messages))

    def start_run(self) -> None:
        case = self.selected_case()
        if case is None:
            self.message_label.setText("请选择用例")
            return
        result = self._readiness()
        if result.blocked:
            self.message_label.setText("；".join(result.blocking_messages))
            return

        device_ids = self.selected_devices()
        payload = self.window.controller.case_to_run_payload(case)
        run_result = self.window.controller.create_run(device_ids[0], [payload])
        run = run_result.get("run", {}) if isinstance(run_result, dict) else {}
        self.window.state.selected_run_id = str(run.get("run_id") or "")
        self.live_output.append(f"开始运行: {self.window.state.selected_run_id}")

    def render_run(self, run: dict[str, Any] | None) -> None:
        if not run:
            return
        self.live_output.setPlainText(format_run_console(run))

    def selected_case(self):
        row = self.case_list.currentRow()
        if 0 <= row < len(self.cases):
            return self.cases[row]
        return None

    def selected_devices(self) -> list[str]:
        selected = [item.text() for item in self.device_list.selectedItems()]
        if not selected and self.devices:
            selected = [self.devices[0]]
        return selected

    def _on_device_selection_changed(self) -> None:
        self.window.state.selected_devices = self.selected_devices()
        self.refresh_readiness()

    def _readiness(self):
        return evaluate_case_readiness(
            self.selected_case(),
            self.window.controller.load_settings(),
            self.selected_devices(),
            self.window.state.preflight,
            run_mode="dual" if self.run_mode_combo.currentText() == "双手机" else "single",
        )


def _case_from_template(template: Any):
    if isinstance(template, SavedCase):
        return template
    if isinstance(template, dict) and template.get("steps"):
        return SavedCase.from_dict(template)
    return template


def _severity_text(severity: Severity) -> str:
    if severity == Severity.OK:
        return "绿色"
    if severity == Severity.WARNING:
        return "黄色"
    return "红色"
