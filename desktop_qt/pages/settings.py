from __future__ import annotations

import copy

from PySide6.QtWidgets import QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget


GROUP_LABELS = {
    "base_web": "基站 Web",
    "ssh": "基站 SSH",
    "traffic": "灌包服务器",
    "common": "通用",
}

GROUP_FIELDS = {
    "base_web": ("host", "username", "password", "log_download_dir"),
    "ssh": ("host", "username", "password", "log_output_dir"),
    "traffic": ("server_host", "server_username", "server_password"),
    "common": ("delay_seconds",),
}


class SettingsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.field_widgets: dict[str, dict[str, QLineEdit]] = {}
        layout = QVBoxLayout(self)
        self.config_file_card = QGroupBox("配置文件")
        toolbar = QHBoxLayout(self.config_file_card)
        self.export_button = QPushButton("导出配置")
        self.import_button = QPushButton("导入配置")
        self.export_button.clicked.connect(self.export_config)
        self.import_button.clicked.connect(self.import_config)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.import_button)
        toolbar.addStretch(1)
        layout.addWidget(self.config_file_card)
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
        values = dict(settings.get(group) or {})
        for field, widget in self.field_widgets[group].items():
            values[field] = widget.text()
        settings[group] = values
        saved = self.window.controller.save_settings(settings)
        self._set_group_values(group, self._group_values(saved, group))

    def export_config(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            "mobile_platform_config.json",
            "JSON 配置 (*.json)",
        )
        if path:
            self.export_config_to_path(path)

    def import_config(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            "",
            "JSON 配置 (*.json)",
        )
        if path:
            self.import_config_from_path(path)

    def export_config_to_path(self, path):
        if hasattr(self.window.controller, "export_settings"):
            return self.window.controller.export_settings(path)
        import json

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.window.controller.load_settings(), handle, ensure_ascii=False, indent=2)
        return path

    def import_config_from_path(self, path) -> dict:
        if hasattr(self.window.controller, "import_settings"):
            imported = self.window.controller.import_settings(path)
        else:
            import json

            with open(path, encoding="utf-8") as handle:
                imported = self.window.controller.save_settings(json.load(handle))
        self._refresh_after_config_import()
        return imported

    def _refresh_after_config_import(self) -> None:
        self.load()
        if hasattr(self.window, "home_page"):
            self.window.home_page.refresh_readiness()
        if hasattr(self.window, "case_library_page"):
            case_library_page = self.window.case_library_page
            if getattr(case_library_page, "_editing_step_index", None) is not None:
                case_library_page.render_selected_step()
            elif getattr(case_library_page, "_selected_operation", None) is not None:
                case_library_page.render_selected_operation()

    def _set_group_values(self, group: str, values: dict) -> None:
        for field, widget in self.field_widgets[group].items():
            widget.setText(str(values.get(field, "")))

    def _group_values(self, settings: dict, group: str) -> dict:
        return settings.get(group) or {}
