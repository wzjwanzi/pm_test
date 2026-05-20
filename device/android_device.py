"""Android device operations implemented with adb shell."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from utils.adb_utils import adb_shell, adb_shell_text


@dataclass(frozen=True)
class UiNode:
    """Minimal UI node extracted from uiautomator XML."""

    resource_id: str
    text: str
    content_desc: str
    class_name: str
    bounds: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)


class AndroidDevice:
    """ADB-backed Android device control helper."""

    def __init__(self, device_id: str):
        self.device_id = device_id

    def search_in_app(
        self,
        search_text: str,
        search_box_id: str | None = None,
        search_btn_id: str | None = None,
    ) -> bool:
        """Type text into a search field and submit using adb shell."""
        if not search_text:
            raise RuntimeError("Missing search text.")

        try:
            search_box = self._find_search_box(search_box_id)
            self.tap(*search_box.center)
            self.clear_focused_text()
            self.input_text(search_text)

            if search_btn_id:
                search_btn = self.find_node(resource_id=search_btn_id)
                if search_btn:
                    self.tap(*search_btn.center)
                    return True

            self.keyevent(66)
            return True
        except Exception as exc:
            print(f"ADB search failed: {exc}")
            return False

    def click_element(self, element_id: str | None = None, text: str | None = None) -> bool:
        """Click an element by resource ID or visible text using adb shell."""
        try:
            node = self.find_node(resource_id=element_id, text=text)
            if not node:
                return False
            self.tap(*node.center)
            return True
        except Exception as exc:
            print(f"ADB click failed: {exc}")
            return False

    def tap(self, x: int, y: int) -> None:
        adb_shell(self.device_id, ["input", "tap", x, y], check=True, timeout=10)

    def keyevent(self, key: str | int) -> None:
        adb_shell(self.device_id, ["input", "keyevent", key], check=True, timeout=10)

    def input_text(self, text: str) -> None:
        adb_shell(self.device_id, ["input", "text", self._escape_input_text(text)], check=True, timeout=20)

    def clear_focused_text(self, max_chars: int = 80) -> None:
        self.keyevent(123)
        for _ in range(max_chars):
            self.keyevent(67)

    def find_node(
        self,
        *,
        resource_id: str | None = None,
        text: str | None = None,
        class_name: str | None = None,
    ) -> UiNode | None:
        for node in self.dump_ui():
            if resource_id and node.resource_id != resource_id:
                continue
            if text and node.text != text and node.content_desc != text:
                continue
            if class_name and node.class_name != class_name:
                continue
            return node
        return None

    def dump_ui(self) -> list[UiNode]:
        """Dump current screen with uiautomator and parse clickable geometry."""
        remote_path = "/sdcard/window_dump.xml"
        adb_shell(self.device_id, ["uiautomator", "dump", remote_path], check=True, timeout=20)
        time.sleep(0.2)
        xml_text = adb_shell_text(self.device_id, ["cat", remote_path], check=True, timeout=20)
        return self._parse_ui_xml(xml_text)

    def _find_search_box(self, search_box_id: str | None = None) -> UiNode:
        if search_box_id:
            node = self.find_node(resource_id=search_box_id)
            if node:
                return node

        common_ids = {
            "search_box",
            "search_edit",
            "et_search",
            "search_input",
            "search_text",
            "searchBox",
        }
        nodes = self.dump_ui()
        for node in nodes:
            short_id = node.resource_id.rsplit("/", 1)[-1]
            if short_id in common_ids:
                return node

        for node in nodes:
            if node.class_name == "android.widget.EditText":
                return node

        raise RuntimeError("Cannot find search input on current screen.")

    def _parse_ui_xml(self, xml_text: str) -> list[UiNode]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise RuntimeError(f"Failed to parse uiautomator dump: {exc}") from exc

        nodes: list[UiNode] = []
        for element in root.iter("node"):
            bounds = self._parse_bounds(element.attrib.get("bounds", ""))
            if not bounds:
                continue
            nodes.append(
                UiNode(
                    resource_id=element.attrib.get("resource-id", ""),
                    text=element.attrib.get("text", ""),
                    content_desc=element.attrib.get("content-desc", ""),
                    class_name=element.attrib.get("class", ""),
                    bounds=bounds,
                )
            )
        return nodes

    def _parse_bounds(self, value: str) -> tuple[int, int, int, int] | None:
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value)
        if not match:
            return None
        return tuple(int(part) for part in match.groups())

    def _escape_input_text(self, text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace(" ", "%s")
            .replace("&", "\\&")
            .replace("|", "\\|")
            .replace("<", "\\<")
            .replace(">", "\\>")
            .replace(";", "\\;")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
