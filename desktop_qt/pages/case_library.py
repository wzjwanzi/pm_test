from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFormLayout, QLineEdit, QListWidget, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

import config
from desktop.case_models import CaseStep, SavedCase
from desktop.case_templates import ACTION_BY_ID, step_from_template


class CaseLibraryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.cases: list[Any] = []
        self.operations: list[dict[str, Any]] = []
        self.parameter_widgets: dict[str, QLineEdit] = {}
        self.parameter_fields: list[dict[str, Any]] = []
        self._editing_step_index: int | None = None
        self._selected_operation: dict[str, Any] | None = None
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.case_list = QListWidget()
        self.add_to_run_button = QPushButton("加入运行")
        left.addWidget(self.case_list)
        left.addWidget(self.add_to_run_button)

        middle = QVBoxLayout()
        self.operation_list = QListWidget()
        self.add_operation_button = QPushButton("添加操作")
        middle.addWidget(self.operation_list)
        middle.addWidget(self.add_operation_button)

        right = QVBoxLayout()
        self.step_list = QListWidget()
        self.parameter_form = QFormLayout()
        self.save_step_button = QPushButton("保存参数")
        self.delete_step_button = QPushButton("删除操作")
        right.addWidget(self.step_list)
        right.addLayout(self.parameter_form)
        right.addWidget(self.save_step_button)
        right.addWidget(self.delete_step_button)

        layout.addLayout(left, 1)
        layout.addLayout(middle, 1)
        layout.addLayout(right, 2)

        self.case_list.currentRowChanged.connect(self.render_selected_case)
        self.step_list.currentRowChanged.connect(self.render_selected_step)
        self.operation_list.currentRowChanged.connect(self.render_selected_operation)
        self.add_operation_button.clicked.connect(self.add_operation_to_case)
        self.save_step_button.clicked.connect(self.save_selected_step_parameters)
        self.delete_step_button.clicked.connect(self.delete_selected_step)
        self.add_to_run_button.clicked.connect(self.add_selected_to_run)
        self.load_cases()
        self.load_operations()

    def load_cases(self) -> None:
        self.cases = [_case_from_template(item) for item in self.window.controller.get_templates()]
        self.case_list.clear()
        for case in self.cases:
            self.case_list.addItem(str(getattr(case, "name", "") or "未命名用例"))
        if self.cases:
            self.case_list.setCurrentRow(0)

    def load_operations(self) -> None:
        if hasattr(self.window.controller, "get_step_templates"):
            self.operations = list(self.window.controller.get_step_templates())
        else:
            self.operations = [
                {
                    "action": template.action,
                    "label": template.label,
                    "group": template.group,
                    "fields": list(template.fields),
                    "defaults": dict(template.defaults),
                }
                for template in ACTION_BY_ID.values()
            ]
        self.operation_list.clear()
        for operation in self.operations:
            self.operation_list.addItem(
                f"{operation.get('group') or '操作'} - {operation.get('label') or operation.get('action')}"
            )

    def render_selected_case(self) -> None:
        case = self.selected_case()
        self.step_list.clear()
        self._clear_parameters()
        for step in getattr(case, "steps", []) if case is not None else []:
            self.step_list.addItem(f"{getattr(step, 'label', '') or getattr(step, 'action', '')}")
        if self.step_list.count():
            self.step_list.setCurrentRow(0)

    def render_selected_operation(self) -> None:
        row = self.operation_list.currentRow()
        if not (0 <= row < len(self.operations)):
            return
        operation = self.operations[row]
        self._selected_operation = operation
        self._editing_step_index = None
        step = _step_from_operation(operation, self.window.controller.load_settings())
        self._render_parameters(operation.get("fields") or [], step.params)

    def render_selected_step(self) -> None:
        case = self.selected_case()
        row = self.step_list.currentRow()
        if case is None or not (0 <= row < len(case.steps)):
            return
        step = case.steps[row]
        operation = _operation_for_action(self.operations, step.action)
        fields = (operation or {}).get("fields") or _fields_from_params(step.params)
        self._selected_operation = operation
        self._editing_step_index = row
        self._render_parameters(fields, step.params)

    def add_operation_to_case(self) -> None:
        case = self.selected_case()
        operation = self.selected_operation()
        if case is None or operation is None:
            return
        step = _step_from_operation(operation, self.window.controller.load_settings())
        step.params.update(self.collect_parameter_values())
        _refresh_generated_command(step)
        case.steps.append(step)
        self._save_case_if_supported(case)
        self.render_selected_case()
        self.step_list.setCurrentRow(len(case.steps) - 1)

    def save_selected_step_parameters(self) -> None:
        case = self.selected_case()
        if case is None or self._editing_step_index is None:
            return
        if not (0 <= self._editing_step_index < len(case.steps)):
            return
        step = case.steps[self._editing_step_index]
        step.params.update(self.collect_parameter_values())
        _refresh_generated_command(step)
        self._save_case_if_supported(case)
        self.render_selected_case()
        self.step_list.setCurrentRow(self._editing_step_index)

    def delete_selected_step(self) -> None:
        case = self.selected_case()
        row = self.step_list.currentRow()
        if case is None or not (0 <= row < len(case.steps)):
            return
        case.steps.pop(row)
        self._editing_step_index = None
        self._save_case_if_supported(case)
        self.render_selected_case()
        if case.steps:
            self.step_list.setCurrentRow(min(row, len(case.steps) - 1))
        else:
            self._clear_parameters()

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

    def selected_operation(self) -> dict[str, Any] | None:
        row = self.operation_list.currentRow()
        if 0 <= row < len(self.operations):
            return self.operations[row]
        return self._selected_operation

    def select_operation(self, action: str) -> None:
        for index, operation in enumerate(self.operations):
            if operation.get("action") == action:
                self.operation_list.setCurrentRow(index)
                self.render_selected_operation()
                return
        raise ValueError(f"Unknown operation: {action}")

    def available_operation_groups(self) -> list[str]:
        return list(dict.fromkeys(str(item.get("group") or "") for item in self.operations if item.get("group")))

    def parameter_value(self, name: str) -> str:
        return self.parameter_widgets[name].text()

    def set_parameter_value(self, name: str, value: str) -> None:
        self.parameter_widgets[name].setText(value)

    def collect_parameter_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        fields = {field["name"]: field for field in self.parameter_fields}
        for name, widget in self.parameter_widgets.items():
            field = fields.get(name, {})
            values[name] = _coerce_value(widget.text(), field.get("type"))
        return values

    def _render_parameters(self, fields: list[dict[str, Any]], params: dict[str, Any]) -> None:
        self._clear_parameters()
        self.parameter_fields = list(fields)
        for field in self.parameter_fields:
            name = str(field.get("name") or "")
            if not name:
                continue
            widget = QLineEdit()
            widget.setText(str(params.get(name, "")))
            self.parameter_widgets[name] = widget
            self.parameter_form.addRow(str(field.get("label") or name), widget)

    def _clear_parameters(self) -> None:
        while self.parameter_form.count():
            item = self.parameter_form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.parameter_widgets.clear()
        self.parameter_fields = []

    def _save_case_if_supported(self, case: SavedCase) -> None:
        if hasattr(self.window.controller, "save_case"):
            self.window.controller.save_case(case)


def _case_from_template(template: Any):
    if isinstance(template, SavedCase):
        return template
    if isinstance(template, dict) and template.get("steps"):
        return SavedCase.from_dict(template)
    return template


def _operation_for_action(operations: list[dict[str, Any]], action: str) -> dict[str, Any] | None:
    for operation in operations:
        if operation.get("action") == action:
            return operation
    if action in ACTION_BY_ID:
        template = ACTION_BY_ID[action]
        return {
            "action": template.action,
            "label": template.label,
            "group": template.group,
            "fields": list(template.fields),
            "defaults": dict(template.defaults),
        }
    return None


def _step_from_operation(operation: dict[str, Any], settings: dict[str, Any]) -> CaseStep:
    action = str(operation.get("action") or "")
    if action in ACTION_BY_ID:
        return step_from_template(action, settings)
    params = dict(operation.get("defaults") or {})
    return CaseStep.new(action, f"{operation.get('group')}-{operation.get('label')}", params)


def _fields_from_params(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"name": name, "label": name, "type": "text"} for name in params]


def _coerce_value(value: str, field_type: Any) -> Any:
    if field_type == "int":
        return int(value or 0)
    if field_type == "bool":
        return value.strip().lower() not in {"0", "false", "no", "off", "否"}
    return value


def _refresh_generated_command(step: CaseStep) -> None:
    if step.action == "traffic_server_downlink_start":
        target = step.params.get("server_downlink_target") or ""
        duration = int(step.params.get("server_downlink_duration") or step.params.get("iperf_duration") or 60000)
        bandwidth = step.params.get("server_downlink_bandwidth") or step.params.get("iperf_bandwidth") or "250m"
        packet_len = int(step.params.get("server_downlink_packet_len") or 1300)
        port = int(step.params.get("server_downlink_port") or step.params.get("iperf_port") or 6011)
        step.params["command"] = f"iperf -u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
    elif step.action == "traffic_server_uplink_receive_start":
        port = int(step.params.get("server_uplink_listen_port") or step.params.get("iperf_port") or 7011)
        step.params["command"] = f"iperf -u -s -i 1 -p {port}"
    elif step.action == "phone_downlink_receive_start":
        port = int(step.params.get("phone_downlink_listen_port") or step.params.get("iperf_port") or 6011)
        step.params["arguments"] = f"-u -s -i 1 -p {port}"
        step.params["command"] = f"adb shell {config.DEVICE_IPERF_BINARY} {step.params['arguments']}"
    elif step.action == "phone_uplink_iperf_start":
        target = step.params.get("phone_uplink_target") or ""
        duration = int(step.params.get("phone_uplink_duration") or step.params.get("iperf_duration") or 6000)
        bandwidth = step.params.get("phone_uplink_bandwidth") or step.params.get("iperf_bandwidth") or "120m"
        packet_len = int(step.params.get("phone_uplink_packet_len") or 1350)
        port = int(step.params.get("phone_uplink_port") or step.params.get("iperf_port") or 7011)
        step.params["arguments"] = f"-u -c {target} -i 1 -t {duration} -b {bandwidth} -l {packet_len} -p {port} -P 1"
        step.params["command"] = f"adb shell {config.DEVICE_IPERF_BINARY} {step.params['arguments']}"
