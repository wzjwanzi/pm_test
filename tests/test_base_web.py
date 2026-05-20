from pm_tests import base_web
from pm_tests.base_web import BaseWebClient


class _Response:
    status_code = 200
    headers = {}
    text = ""

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_base_web_login_submits_encoded_verify_code(monkeypatch):
    posts = []

    class FakeSession:
        def post(self, url, data=None, **kwargs):
            posts.append((url, dict(data or {})))
            if data and data.get("flag") == "getVerifyCode":
                return _Response({"code": 200, "msg": "OK", "verifyCode": "6633qB28YfWfYi2attm5I7iIa5bC6EIN"})
            return _Response({"success": True, "msg": "session-id", "data": {"firstLogin": False}})

    monkeypatch.setattr(base_web.requests, "Session", FakeSession)

    client = BaseWebClient({"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"})
    result = client.login()

    login_payload = posts[-1][1]
    assert result["success"] is True
    assert login_payload["flag"] == "login"
    assert "verifyCode" in login_payload
    assert login_payload["verifyCode"] != "6633qB28YfWfYi2attm5I7iIa5bC6EIN"
    assert base_web._decode_submitted_verify_code(login_payload["verifyCode"]) == "65gh"


def test_stop_capture_falls_back_to_artifacts_dir_when_download_dir_is_not_writable(monkeypatch, tmp_path):
    class FakeSession:
        def post(self, url, data=None, json=None, **kwargs):
            if data and data.get("flag") == "getVerifyCode":
                return _Response({"code": 200, "verifyCode": "6633qB28YfWfYi2attm5I7iIa5bC6EIN"})
            if data and data.get("flag") == "login":
                return _Response({"success": True, "msg": "session-id", "data": {}})
            return _Response({"code": 200, "success": True, "filepath": "/tmp/web.pcap"})

    calls = []

    def fake_download(self, remote_path, local_path):
        calls.append(local_path)
        if len(calls) == 1:
            raise PermissionError("denied")
        local_path.write_bytes(b"pcap")

    monkeypatch.setattr(base_web.requests, "Session", FakeSession)
    monkeypatch.setattr(base_web.config, "PM_ARTIFACTS_DIR", tmp_path / "artifacts")
    monkeypatch.setattr(BaseWebClient, "_download_file", fake_download)

    client = BaseWebClient({"host": "192.168.13.236", "port": 8400, "username": "root", "password": "5GNR@root"})
    result = client.stop_capture(type("Capture", (), {"select_msg": "CP"})(), download_dir=tmp_path / "blocked")

    assert result["success"] is True
    assert result["local_path"].startswith(str(tmp_path / "artifacts"))
    assert result["download_dir_fallback_from"] == str(tmp_path / "blocked")
    assert len(calls) == 2
