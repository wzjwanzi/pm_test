import json

from pm_tests.base_station_config import BaseStationConfigClient


class _Response:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _Session:
    def __init__(self):
        self.posts = []

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, data, timeout))
        if data and data.get("flag") == "getVerifyCode":
            return _Response({"code": 200, "verifyCode": ""})
        if data and data.get("flag") == "login":
            return _Response({"success": True, "msg": "session-1"})
        if data and data.get("flag") == "get_CellId_list":
            return _Response({"rows": [{"cellid": "1", "node": "Device.Services.FAPService.1.CellConfig.1"}]})
        if data and data.get("flag") == "get_multi_ins":
            return _Response({"count": "1", "row": [{"indexid_id": "1"}]})
        if data and data.get("flag") == "get_para_vals":
            return _Response({"data": {"NR.RAN.RF.PhyCellID": "236", "NR.RAN.Common.CellIdWithinGnb": "1"}})
        if data and data.get("flag") == "get_FAP_info":
            return _Response({"data": {"PhyCellID": "236", "CellIdWithinGnb": "1"}})
        if data and data.get("flag") == "set_para_vals":
            return _Response({"success": True, "code": "200"})
        return _Response({"success": False, "code": "-1", "msg": "unexpected"})


def test_base_station_config_client_discovers_cell_nodes(monkeypatch):
    import pm_tests.base_web as base_web

    monkeypatch.setattr(base_web.requests, "Session", _Session)
    client = BaseStationConfigClient({"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"})

    nodes = client.discover_nodes()

    assert [node.path for node in nodes] == ["Device.Services.FAPService.1.CellConfig.1."]
    assert client.session_id == "session-1"


def test_base_station_config_client_reads_and_writes_node_parameters(monkeypatch):
    import pm_tests.base_web as base_web

    monkeypatch.setattr(base_web.requests, "Session", _Session)
    client = BaseStationConfigClient({"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"})

    values = client.get_node_parameters("Device.Services.FAPService.1.CellConfig.1")
    result = client.set_node_parameters("Device.Services.FAPService.1.CellConfig.1", {"NR.RAN.RF.PhyCellID": "237"})

    assert values["NR.RAN.RF.PhyCellID"] == "236"
    assert result["code"] == "200"
    set_payload = client.session.posts[-1][1]
    assert set_payload["flag"] == "set_para_vals"
    assert set_payload["node"] == "Device.Services.FAPService.1.CellConfig.1."
    assert json.loads(set_payload["attr"]) == {"NR.RAN.RF.PhyCellID": "237"}


def test_base_station_config_client_uses_lightweight_common_parameter_api(monkeypatch):
    import pm_tests.base_web as base_web

    monkeypatch.setattr(base_web.requests, "Session", _Session)
    client = BaseStationConfigClient({"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"})

    values = client.get_common_parameters("Device.Services.FAPService.1.CellConfig.1")
    client.set_common_parameters("Device.Services.FAPService.1.CellConfig.1", {"PhyCellID": "237"})

    assert values == {"CellIdWithinGnb": "1", "PhyCellID": "236"}
    set_payload = client.session.posts[-1][1]
    assert json.loads(set_payload["attr"]) == {"NR.RAN.RF.PhyCellID": "237"}
