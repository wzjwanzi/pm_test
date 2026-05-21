from __future__ import annotations

import copy

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit, QPushButton, QVBoxLayout, QWidget


GROUP_LABELS = {
    "base_web": "基站 Web",
    "ssh": "基站 SSH",
    "traffic": "灌包服务器",
    "device_mapping": "多设备映射",
    "common": "通用",
}

GROUP_FIELDS = {
    "base_web": ("host", "username", "password", "log_download_dir"),
    "ssh": ("host", "username", "password", "log_output_dir"),
    "traffic": ("server_host", "server_username", "server_password", "server_downlink_target", "phone_uplink_target"),
    "device_mapping": ("device_overrides",),
    "common": ("delay_seconds",),
}


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.field_widgets: dict[str, dict[str, QLineEdit]] = {}
        layout = QVBoxLayout(self)
        self.cards: dict[str, QGroupBox] = {}
        for group in GROUP_LABELS:
            card = QGroupBox(GROUP_LABELS[group])
            form = QFormLayout(card)
            self.field_widgets[group] = {}
            for field in GROUP_FIELDS[group]:
                widget = QLineEdit()
                self.field_widgets[group][field] = widget
                form.addRow(field, widget)
            save_button = QPushButton("保存")
            save_button.clicked.connect(lambda _checked=False, group_name=group: self.save_group(group_name))
            form.addRow(save_button)
            self.cards[group] = card
            layout.addWidget(card)
        self.load()

    def load(self) -> None:
        settings = self.window.controller.load_settings()
        for group, widgets in self.field_widgets.items():
            values = self._group_values(settings, group)
            for field, widget in widgets.items():
                widget.setText(str(values.get(field, "")))

    def set_field_value(self, group: str, field: str, value: str) -> None:
        self.field_widgets[group][field].setText(value)

    def save_group(self, group: str) -> None:
        settings = copy.deepcopy(self.window.controller.load_settings())
        if group == "device_mapping":
            target = dict(settings.get("traffic") or {})
            target["device_overrides"] = self.field_widgets[group]["device_overrides"].text()
            settings["traffic"] = target
        else:
            values = dict(settings.get(group) or {})
            for field, widget in self.field_widgets[group].items():
                values[field] = widget.text()
            settings[group] = values
        saved = self.window.controller.save_settings(settings)
        self._set_group_values(group, self._group_values(saved, group))

    def _set_group_values(self, group: str, values: dict) -> None:
        for field, widget in self.field_widgets[group].items():
            widget.setText(str(values.get(field, "")))

    def _group_values(self, settings: dict, group: str) -> dict:
        if group == "device_mapping":
            traffic = settings.get("traffic") or {}
            return {"device_overrides": traffic.get("device_overrides", "")}
        return settings.get(group) or {}
