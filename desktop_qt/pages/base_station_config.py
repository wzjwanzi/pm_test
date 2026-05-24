from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class BaseStationConfigPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._loaded_values: dict[str, str] = {}
        self._nodes_by_category: dict[str, list[dict[str, str]]] = {}

        layout = QHBoxLayout(self)
        left = QVBoxLayout()
        middle = QVBoxLayout()
        right = QVBoxLayout()

        self.refresh_button = QPushButton("刷新节点")
        self.category_list = QListWidget()
        self.node_list = QListWidget()
        self.node_path_edit = QLineEdit()
        self.node_path_edit.setPlaceholderText("Device.Services.FAPService.1.CellConfig.1.")
        self.load_button = QPushButton("读取参数")
        self.status_label = QLabel("")

        left.addWidget(self.refresh_button)
        left.addWidget(self.category_list, 1)
        middle.addWidget(QLabel("子节点"))
        middle.addWidget(self.node_list, 1)
        left.addWidget(QLabel("节点路径"))
        left.addWidget(self.node_path_edit)
        left.addWidget(self.load_button)
        left.addWidget(self.status_label)

        self.param_table = QTableWidget(0, 2)
        self.param_table.setHorizontalHeaderLabels(["参数", "值"])
        self.param_table.horizontalHeader().setStretchLastSection(True)
        self.save_button = QPushButton("保存改动")

        right.addWidget(self.param_table, 1)
        right.addWidget(self.save_button)

        layout.addLayout(left, 1)
        layout.addLayout(middle, 2)
        layout.addLayout(right, 4)

        self.refresh_button.clicked.connect(self.refresh_nodes)
        self.load_button.clicked.connect(self.load_current_node)
        self.save_button.clicked.connect(self.save_changes)
        self.category_list.currentItemChanged.connect(lambda _current, _previous: self.render_category_nodes())
        self.node_list.currentItemChanged.connect(lambda _current, _previous: self.select_current_node())
        self._init_categories()

    def _init_categories(self) -> None:
        self.category_list.clear()
        for label, mode in (("主页", "home"), ("常用参数", "common")):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, mode)
            self.category_list.addItem(item)
        self.category_list.setCurrentRow(1)

    def refresh_nodes(self) -> None:
        self.status_label.setText("正在刷新节点...")
        self.node_list.clear()
        try:
            nodes = self.window.controller.discover_base_station_nodes()
        except Exception as exc:
            self.status_label.setText(f"刷新失败: {exc}")
            return
        self._nodes_by_category = {
            "home": [
                {
                    "path": str(node.get("path") or ""),
                    "label": str(node.get("label") or node.get("path") or ""),
                    "mode": "full",
                }
                for node in nodes
            ],
            "common": [
                {
                    "path": str(node.get("path") or ""),
                    "label": str(node.get("label") or node.get("path") or ""),
                    "mode": "common",
                }
                for node in nodes
            ],
        }
        self.render_category_nodes()
        self.status_label.setText(f"已发现 {len(nodes)} 个节点，点击“读取参数”后加载")

    def render_category_nodes(self) -> None:
        self.node_list.clear()
        mode = self._selected_category()
        nodes = self._nodes_by_category.get(mode, [])
        for node in nodes:
            path = str(node.get("path") or "")
            label = str(node.get("label") or path)
            item = QListWidgetItem(f"{label}  {path}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setData(Qt.ItemDataRole.UserRole + 1, str(node.get("mode") or "full"))
            self.node_list.addItem(item)
        if self.node_list.count():
            self.node_list.setCurrentRow(0)
        else:
            self.param_table.setRowCount(0)
            self._loaded_values = {}

    def select_current_node(self) -> None:
        node = self._selected_node()
        if not node:
            return
        self.node_path_edit.setText(node)
        self.param_table.setRowCount(0)
        self._loaded_values = {}
        self.status_label.setText("已选择节点，点击“读取参数”后加载")

    def load_current_node(self) -> None:
        node = self._selected_node()
        if not node:
            return
        self.node_path_edit.setText(node)
        self.status_label.setText("正在读取参数...")
        try:
            if self._selected_node_mode() == "common":
                values = self.window.controller.get_base_station_common_parameters(node)
            else:
                values = self.window.controller.get_base_station_node_parameters(node)
        except Exception as exc:
            self.status_label.setText(f"读取失败: {exc}")
            return
        self._loaded_values = {str(key): str(value) for key, value in values.items()}
        self._render_parameters(self._loaded_values)
        self.status_label.setText(f"已读取 {len(values)} 个参数")

    def save_changes(self) -> None:
        node = self._selected_node()
        if not node:
            return
        changes = self._changed_values()
        if not changes:
            self.status_label.setText("没有改动")
            return
        self.status_label.setText("正在保存改动...")
        try:
            if self._selected_node_mode() == "common":
                result = self.window.controller.set_base_station_common_parameters(node, changes)
            else:
                result = self.window.controller.set_base_station_node_parameters(node, changes)
        except Exception as exc:
            self.status_label.setText(f"保存失败: {exc}")
            return
        for key, value in changes.items():
            self._loaded_values[key] = value
        code = result.get("code") or "200"
        self.status_label.setText(f"保存完成: {len(changes)} 项, code={code}")

    def _selected_node(self) -> str:
        current = self.node_list.currentItem()
        if current is not None:
            path = current.data(Qt.ItemDataRole.UserRole)
            if path:
                return str(path)
        return self.node_path_edit.text().strip()

    def _selected_node_mode(self) -> str:
        current = self.node_list.currentItem()
        if current is not None:
            mode = current.data(Qt.ItemDataRole.UserRole + 1)
            if mode:
                return str(mode)
        return "full"

    def _selected_category(self) -> str:
        current = self.category_list.currentItem()
        if current is None:
            return "common"
        mode = current.data(Qt.ItemDataRole.UserRole)
        return str(mode or "common")

    def _render_parameters(self, values: dict[str, str]) -> None:
        self.param_table.setRowCount(0)
        for row, (key, value) in enumerate(values.items()):
            self.param_table.insertRow(row)
            key_item = QTableWidgetItem(key)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.param_table.setItem(row, 0, key_item)
            self.param_table.setItem(row, 1, QTableWidgetItem(value))

    def _changed_values(self) -> dict[str, str]:
        changes: dict[str, str] = {}
        for row in range(self.param_table.rowCount()):
            key_item = self.param_table.item(row, 0)
            value_item = self.param_table.item(row, 1)
            if key_item is None or value_item is None:
                continue
            key = key_item.text()
            value = value_item.text()
            if self._loaded_values.get(key) != value:
                changes[key] = value
        return changes
