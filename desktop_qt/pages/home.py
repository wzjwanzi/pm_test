from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
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
from desktop.case_operations import apply_device_overrides_to_payload
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
        self.device_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItems(["单手机", "双手机"])
        self.run_mode_hint = QLabel("单手机：只运行当前选中的一台设备；双手机：对选中的多台设备分别创建运行任务。")
        self.device_selection_hint = QLabel("")
        device_layout = QVBoxLayout(self.device_group)
        device_layout.addWidget(self.device_list)
        device_layout.addWidget(self.run_mode_combo)
        device_layout.addWidget(self.run_mode_hint)
        device_layout.addWidget(self.device_selection_hint)

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
        self.run_mode_combo.currentIndexChanged.connect(lambda _index: self._on_run_mode_changed())
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
        self._update_selection_hint()

    def load_cases(self) -> None:
        self.cases = [_case_from_template(item) for item in self.window.controller.get_templates()]
        self.case_list.clear()
        for case in self.cases:
            self.case_list.addItem(str(getattr(case, "name", "") or "未命名用例"))
        if self.cases:
            self.case_list.setCurrentRow(0)
            self.window.state.selected_case = self.cases[0]

    def refresh_readiness(self) -> None:
        self._update_selection_hint()
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
        self.message_label.setText("; ".join(result.blocking_messages))

    def start_run(self) -> None:
        case = self.selected_case()
        if case is None:
            self.message_label.setText("请选择用例")
            return
        result = self._readiness()
        if result.blocked:
            self.message_label.setText("; ".join(result.blocking_messages))
            return

        device_ids = self.selected_devices()
        settings = self.window.controller.load_settings()
        run_ids = []
        for device_id in device_ids:
            payload = apply_device_overrides_to_payload(
                self.window.controller.case_to_run_payload(case),
                settings,
                device_id,
            )
            run_result = self.window.controller.create_run(device_id, [payload])
            run = run_result.get("run", {}) if isinstance(run_result, dict) else {}
            run_id = str(run.get("run_id") or "")
            if run_id:
                run_ids.append(run_id)
        self.window.state.selected_run_ids = run_ids
        self.window.state.selected_run_id = run_ids[-1] if run_ids else ""
        self.live_output.append(f"开始运行: {', '.join(run_ids)}")

    def render_run(self, run: dict[str, Any] | None) -> None:
        if not run:
            return
        scrollbar = self.live_output.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum()
        previous_value = scrollbar.value()
        self.live_output.setPlainText(format_run_console(run))
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(min(previous_value, scrollbar.maximum()))

    def selected_case(self):
        row = self.case_list.currentRow()
        if 0 <= row < len(self.cases):
            return self.cases[row]
        return None

    def selected_devices(self) -> list[str]:
        if not self._is_dual_mode():
            current = self.device_list.currentItem()
            if current is not None:
                return [current.text()]
            return [self.devices[0]] if self.devices else []
        selected = [item.text() for item in self.device_list.selectedItems()]
        if not selected and self.devices:
            selected = [self.devices[0]]
        return selected

    def _on_device_selection_changed(self) -> None:
        self.window.state.selected_devices = self.selected_devices()
        self.refresh_readiness()

    def _on_run_mode_changed(self) -> None:
        if self._is_dual_mode():
            self.device_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        else:
            self.device_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.window.state.selected_devices = self.selected_devices()
        self.refresh_readiness()

    def _readiness(self):
        return evaluate_case_readiness(
            self.selected_case(),
            self.window.controller.load_settings(),
            self.selected_devices(),
            self.window.state.preflight,
            run_mode="dual" if self._is_dual_mode() else "single",
        )

    def _is_dual_mode(self) -> bool:
        return self.run_mode_combo.currentIndex() == 1

    def _update_selection_hint(self) -> None:
        selected_count = len([item for item in self.device_list.selectedItems()])
        if self._is_dual_mode():
            self.device_selection_hint.setText(
                f"双手机模式：按住 Ctrl 可多选设备，至少选择两台设备；当前已选择 {selected_count} 台。"
            )
        else:
            self.device_selection_hint.setText("单手机模式：点击一个设备序号即可运行该设备；双手机模式可按住 Ctrl 多选设备。")


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
