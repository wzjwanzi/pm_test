from __future__ import annotations

import copy
from typing import Any

import config
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget


class DevicesPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        layout = QHBoxLayout(self)
        self.device_list = QListWidget()
        self.refresh_button = QPushButton("刷新设备")
        self.inspect_button = QPushButton("检查设备")
        self.phone_ip_edit = QLineEdit()
        self.downlink_port_edit = QLineEdit()
        self.uplink_port_edit = QLineEdit()
        self.server_ip_edit = QLineEdit()
        self.downlink_bandwidth_edit = QLineEdit()
        self.uplink_bandwidth_edit = QLineEdit()
        self.downlink_duration_edit = QLineEdit()
        self.uplink_duration_edit = QLineEdit()
        self.ping_count_edit = QLineEdit()
        self.save_button = QPushButton("保存映射")

        self.left_panel = QGroupBox("设备管理")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.addWidget(self.refresh_button)
        left_layout.addWidget(self.inspect_button)
        left_layout.addStretch(1)

        self.middle_panel = QGroupBox("设备序号")
        middle_layout = QVBoxLayout(self.middle_panel)
        middle_layout.addWidget(QLabel("ADB 设备 / 已配置设备"))
        middle_layout.addWidget(self.device_list)

        self.right_panel = QGroupBox("配置项")
        right_layout = QVBoxLayout(self.right_panel)
        self.mapping_form = QFormLayout()
        self.mapping_form.addRow("手机 IP", self.phone_ip_edit)
        self.mapping_form.addRow("下行端口", self.downlink_port_edit)
        self.mapping_form.addRow("上行端口", self.uplink_port_edit)
        self.mapping_form.addRow("灌包服务器 IP", self.server_ip_edit)
        self.mapping_form.addRow("下行带宽", self.downlink_bandwidth_edit)
        self.mapping_form.addRow("上行带宽", self.uplink_bandwidth_edit)
        self.mapping_form.addRow("下行时长", self.downlink_duration_edit)
        self.mapping_form.addRow("上行时长", self.uplink_duration_edit)
        self.mapping_form.addRow("Ping 次数", self.ping_count_edit)
        right_layout.addLayout(self.mapping_form)
        right_layout.addWidget(self.save_button)
        right_layout.addStretch(1)

        layout.addWidget(self.left_panel, 1)
        layout.addWidget(self.middle_panel, 2)
        layout.addWidget(self.right_panel, 3)

        self.refresh_button.clicked.connect(self.refresh_devices)
        self.device_list.currentItemChanged.connect(lambda _current, _previous: self.load_selected_mapping())
        self.save_button.clicked.connect(self.save_mapping)
        self.refresh_devices()

    def refresh_devices(self) -> None:
        current_id = self.device_list.currentItem().text() if self.device_list.currentItem() else ""
        device_ids = list(self.window.controller.refresh_devices())
        settings = self.window.controller.load_settings()
        configured_ids = list(((settings.get("traffic") or {}).get("device_overrides") or {}).keys())
        merged_ids = list(dict.fromkeys([*device_ids, *configured_ids]))

        self.device_list.clear()
        self.device_list.addItems(merged_ids)
        if not merged_ids:
            self._clear_fields()
            return
        target_id = current_id if current_id in merged_ids else merged_ids[0]
        matches = self.device_list.findItems(target_id, Qt.MatchFlag.MatchExactly)
        if matches:
            self.device_list.setCurrentItem(matches[0])
        else:
            self.device_list.setCurrentRow(0)
        self.load_selected_mapping()

    def set_mapping(
        self,
        device_id: str,
        *,
        phone_ip: str,
        downlink_port: str,
        uplink_port: str,
        server_ip: str | None = None,
        downlink_bandwidth: str | None = None,
        uplink_bandwidth: str | None = None,
        downlink_duration: str | None = None,
        uplink_duration: str | None = None,
    ) -> None:
        matches = self.device_list.findItems(device_id, Qt.MatchFlag.MatchExactly)
        if matches:
            self.device_list.setCurrentItem(matches[0])
        else:
            self.device_list.addItem(device_id)
            self.device_list.setCurrentRow(self.device_list.count() - 1)
        self.phone_ip_edit.setText(phone_ip)
        self.downlink_port_edit.setText(downlink_port)
        self.uplink_port_edit.setText(uplink_port)
        if server_ip is not None:
            self.server_ip_edit.setText(server_ip)
        if downlink_bandwidth is not None:
            self.downlink_bandwidth_edit.setText(downlink_bandwidth)
        if uplink_bandwidth is not None:
            self.uplink_bandwidth_edit.setText(uplink_bandwidth)
        if downlink_duration is not None:
            self.downlink_duration_edit.setText(downlink_duration)
        if uplink_duration is not None:
            self.uplink_duration_edit.setText(uplink_duration)

    def load_selected_mapping(self) -> None:
        current = self.device_list.currentItem()
        if current is None:
            self._clear_fields()
            return
        settings = self.window.controller.load_settings()
        traffic = settings.get("traffic") or {}
        mapping = ((traffic.get("device_overrides") or {}).get(current.text()) or {})
        self.phone_ip_edit.setText(str(mapping.get("phone_ip") or mapping.get("server_downlink_target") or ""))
        self.downlink_port_edit.setText(str(mapping.get("downlink_port") or mapping.get("server_downlink_port") or mapping.get("phone_downlink_listen_port") or ""))
        self.uplink_port_edit.setText(str(mapping.get("uplink_port") or mapping.get("server_uplink_listen_port") or mapping.get("phone_uplink_port") or ""))
        self.server_ip_edit.setText(str(mapping.get("traffic_server_ip") or mapping.get("phone_uplink_target") or _default_phone_target(traffic)))
        self.downlink_bandwidth_edit.setText(str(mapping.get("server_downlink_bandwidth") or traffic.get("server_downlink_bandwidth") or "250m"))
        self.uplink_bandwidth_edit.setText(str(mapping.get("phone_uplink_bandwidth") or traffic.get("phone_uplink_bandwidth") or "120m"))
        self.downlink_duration_edit.setText(str(mapping.get("server_downlink_duration") or traffic.get("server_downlink_duration") or 60000))
        self.uplink_duration_edit.setText(str(mapping.get("phone_uplink_duration") or traffic.get("phone_uplink_duration") or 6000))
        self.ping_count_edit.setText(str(mapping.get("server_ping_count") if "server_ping_count" in mapping else traffic.get("server_ping_count", 5)))

    def save_mapping(self) -> None:
        current = self.device_list.currentItem()
        if current is None:
            return
        device_id = current.text()
        settings = copy.deepcopy(self.window.controller.load_settings())
        traffic = dict(settings.get("traffic") or {})
        overrides = dict(traffic.get("device_overrides") or {})
        overrides[device_id] = self._mapping_from_fields(traffic)
        traffic["device_overrides"] = overrides
        settings["traffic"] = traffic
        self.window.controller.save_settings(settings)
        self._refresh_related_pages()

    def _mapping_from_fields(self, traffic: dict[str, Any]) -> dict[str, Any]:
        phone_ip = self.phone_ip_edit.text().strip()
        downlink_port = _int_or_default(self.downlink_port_edit.text(), traffic.get("server_downlink_port") or 6011)
        uplink_port = _int_or_default(self.uplink_port_edit.text(), traffic.get("phone_uplink_port") or 7011)
        server_ip = self.server_ip_edit.text().strip() or _default_phone_target(traffic)
        downlink_bandwidth = self.downlink_bandwidth_edit.text().strip() or str(traffic.get("server_downlink_bandwidth") or "250m")
        uplink_bandwidth = self.uplink_bandwidth_edit.text().strip() or str(traffic.get("phone_uplink_bandwidth") or "120m")
        downlink_duration = _int_or_default(self.downlink_duration_edit.text(), traffic.get("server_downlink_duration") or 60000)
        uplink_duration = _int_or_default(self.uplink_duration_edit.text(), traffic.get("phone_uplink_duration") or 6000)
        ping_count = _int_or_default(self.ping_count_edit.text(), traffic.get("server_ping_count") if "server_ping_count" in traffic else 5)
        return {
            "phone_ip": phone_ip,
            "server_downlink_target": phone_ip,
            "server_ping_target": phone_ip,
            "ping_target": phone_ip,
            "downlink_port": downlink_port,
            "server_downlink_port": downlink_port,
            "phone_downlink_listen_port": downlink_port,
            "uplink_port": uplink_port,
            "server_uplink_listen_port": uplink_port,
            "phone_uplink_port": uplink_port,
            "traffic_server_ip": server_ip,
            "phone_uplink_target": server_ip,
            "phone_ping_target": server_ip,
            "server_downlink_bandwidth": downlink_bandwidth,
            "phone_uplink_bandwidth": uplink_bandwidth,
            "server_downlink_duration": downlink_duration,
            "phone_uplink_duration": uplink_duration,
            "server_ping_count": ping_count,
        }

    def _refresh_related_pages(self) -> None:
        home_page = getattr(self.window, "home_page", None)
        if home_page is not None:
            home_page.refresh_devices()
            home_page.refresh_readiness()

    def _clear_fields(self) -> None:
        for field in (
            self.phone_ip_edit,
            self.downlink_port_edit,
            self.uplink_port_edit,
            self.server_ip_edit,
            self.downlink_bandwidth_edit,
            self.uplink_bandwidth_edit,
            self.downlink_duration_edit,
            self.uplink_duration_edit,
            self.ping_count_edit,
        ):
            field.clear()


def _int_or_default(value: str, default: Any) -> int:
    text = str(value or "").strip()
    if text == "":
        return int(default or 0)
    return int(text)


def _default_phone_target(traffic: dict[str, Any]) -> str:
    overrides = traffic.get("device_overrides") if isinstance(traffic, dict) else {}
    if isinstance(overrides, dict):
        for values in overrides.values():
            if isinstance(values, dict):
                target = values.get("traffic_server_ip") or values.get("phone_uplink_target")
                if target:
                    return str(target).strip()
    return config.TRAFFIC_SERVER_PHONE_TARGET
