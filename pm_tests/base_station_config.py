"""Basestation configuration discovery and update helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pm_tests.base_web import BaseWebClient


DEFAULT_DISCOVERY_ROOTS = (
    "Device.Services.FAPService.1.CellConfig.",
)


@dataclass(frozen=True, slots=True)
class BaseStationNode:
    path: str
    label: str


class BaseStationConfigClient(BaseWebClient):
    """Client for generic basestation configuration CGI endpoints."""

    def __init__(self, settings: dict[str, Any] | None = None):
        super().__init__(settings)
        self.session_id = ""

    def login(self) -> dict[str, Any]:
        data = super().login()
        if data.get("msg"):
            self.session_id = str(data.get("msg") or "")
        return data

    def discover_nodes(self) -> list[BaseStationNode]:
        """Discover editable leaf configuration nodes known by the Web UI."""
        self.login()
        nodes: dict[str, BaseStationNode] = {}
        for root in DEFAULT_DISCOVERY_ROOTS:
            for child in self._get_multi_instances(root):
                nodes[child.path] = child
        for cell in self._get_cell_nodes():
            nodes[cell.path] = cell
        return [nodes[key] for key in sorted(nodes)]

    def get_node_parameters(self, node: str) -> dict[str, str]:
        self.login()
        node = _normalize_node(node)
        data = self._post_config(
            "/public/cgi-bin/base_intrface.cgi",
            {
                "flag": "get_para_vals",
                "node": node,
            },
        )
        values = data.get("data")
        if not isinstance(values, dict):
            return {}
        return {str(key): "" if value is None else str(value) for key, value in sorted(values.items())}

    def get_common_parameters(self, node: str) -> dict[str, str]:
        self.login()
        data = self._post_config(
            "/public/cgi-bin/generalParameters.cgi",
            {
                "flag": "get_FAP_info",
                "sear": _normalize_node(node).rstrip("."),
            },
        )
        values = data.get("data")
        if not isinstance(values, dict):
            return {}
        return {str(key): "" if value is None else str(value) for key, value in sorted(values.items())}

    def set_node_parameters(self, node: str, values: dict[str, Any]) -> dict[str, Any]:
        self.login()
        node = _normalize_node(node)
        attr = {str(key): "" if value is None else str(value) for key, value in values.items()}
        if not attr:
            return {"success": True, "code": "200", "message": "No changes."}
        return self._post_config(
            "/public/cgi-bin/base_intrface.cgi",
            {
                "flag": "set_para_vals",
                "node": node,
                "attr": json.dumps(attr, ensure_ascii=False),
            },
        )

    def set_common_parameters(self, node: str, values: dict[str, Any]) -> dict[str, Any]:
        mapped = {_COMMON_PARAMETER_SET_KEYS.get(str(key), str(key)): value for key, value in values.items()}
        return self.set_node_parameters(node, mapped)

    def _get_cell_nodes(self) -> list[BaseStationNode]:
        data = self._post_config(
            "/public/cgi-bin/overall.cgi",
            {
                "flag": "get_CellId_list",
            },
        )
        rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        nodes: list[BaseStationNode] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("node") or "").strip()
            if not path:
                continue
            cell_id = str(row.get("cellid") or path.rstrip(".").rsplit(".", 1)[-1])
            nodes.append(BaseStationNode(_normalize_node(path), f"Cell {cell_id}"))
        return nodes

    def _get_multi_instances(self, root: str) -> list[BaseStationNode]:
        data = self._post_config(
            "/public/cgi-bin/base_intrface.cgi",
            {
                "flag": "get_multi_ins",
                "node": _normalize_node(root),
            },
        )
        rows = data.get("row") if isinstance(data.get("row"), list) else []
        nodes: list[BaseStationNode] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            index = str(row.get("indexid_id") or "").strip()
            if not index:
                continue
            path = f"{_normalize_node(root)}{index}."
            nodes.append(BaseStationNode(path, path.rstrip(".")))
        return nodes

    def _post_config(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(payload)
        payload.setdefault("account", str(self.settings.get("username") or "root"))
        payload.setdefault("sessionid", self.session_id)
        response = self.session.post(self._url(path), data=payload, timeout=20)
        data = self._parse_json(response, str(payload.get("flag") or path))
        code = str(data.get("code") or "")
        if data.get("success") is False and code not in {"", "200"}:
            raise RuntimeError(str(data.get("msg") or f"Base station config request failed: {code}"))
        return data


def _normalize_node(node: str) -> str:
    text = str(node or "").strip()
    if text and not text.endswith("."):
        text += "."
    return text


_COMMON_PARAMETER_SET_KEYS = {
    "PhyCellID": "NR.RAN.RF.PhyCellID",
    "CellIdWithinGnb": "NR.RAN.Common.CellIdWithinGnb",
    "RouteIndexList": "NR.RAN.RouteIndexList",
}
