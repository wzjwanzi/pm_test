from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget


class DevicesPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QVBoxLayout(self)
        self.device_list = QListWidget()
        self.refresh_button = QPushButton("刷新设备")
        self.inspect_button = QPushButton("检查设备")
        self.phone_ip_edit = QLineEdit()
        self.downlink_port_edit = QLineEdit()
        self.uplink_port_edit = QLineEdit()
        self.save_button = QPushButton("保存映射")

        form = QFormLayout()
        form.addRow("手机 IP", self.phone_ip_edit)
        form.addRow("下行端口", self.downlink_port_edit)
        form.addRow("上行端口", self.uplink_port_edit)

        layout.addWidget(self.refresh_button)
        layout.addWidget(self.device_list)
        layout.addWidget(self.inspect_button)
        layout.addLayout(form)
        layout.addWidget(self.save_button)

        self.refresh_button.clicked.connect(self.refresh_devices)
        self.save_button.clicked.connect(self.save_mapping)
        self.refresh_devices()

    def refresh_devices(self) -> None:
        self.device_list.clear()
        self.device_list.addItems(self.window.controller.refresh_devices())
        if self.device_list.count():
            self.device_list.setCurrentRow(0)

    def set_mapping(self, device_id: str, *, phone_ip: str, downlink_port: str, uplink_port: str) -> None:
        matches = self.device_list.findItems(device_id, Qt.MatchFlag.MatchExactly)
        if matches:
            self.device_list.setCurrentItem(matches[0])
        else:
            self.device_list.addItem(device_id)
            self.device_list.setCurrentRow(self.device_list.count() - 1)
        self.phone_ip_edit.setText(phone_ip)
        self.downlink_port_edit.setText(downlink_port)
        self.uplink_port_edit.setText(uplink_port)

    def save_mapping(self) -> None:
        current = self.device_list.currentItem()
        if current is None:
            return
        device_id = current.text()
        settings = copy.deepcopy(self.window.controller.load_settings())
        traffic = dict(settings.get("traffic") or {})
        overrides = dict(traffic.get("device_overrides") or {})
        overrides[device_id] = {
            "phone_ip": self.phone_ip_edit.text().strip(),
            "downlink_port": int(self.downlink_port_edit.text() or 0),
            "uplink_port": int(self.uplink_port_edit.text() or 0),
        }
        traffic["device_overrides"] = overrides
        settings["traffic"] = traffic
        self.window.controller.save_settings(settings)
