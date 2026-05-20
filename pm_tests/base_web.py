"""Helpers for the basestation Web UI."""

from __future__ import annotations

import hashlib
import json
import random
import string
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

import config
from app_settings import get_base_web_settings


@dataclass
class BaseWebCaptureSession:
    """A basestation Web capture session handle."""

    select_msg: str
    transmit_ip: str
    started_at: str


class BaseWebClient:
    """Minimal client for the basestation Web CGI endpoints."""

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or get_base_web_settings()
        host = self.settings.get("host", "")
        port = int(self.settings.get("port") or 8400)
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self._logged_in = False

    def login(self) -> dict[str, Any]:
        """Authenticate and keep the session cookie."""
        if self._logged_in:
            return {"success": True, "cached": True}

        verify_code = self._get_encoded_verify_code()
        password = str(self.settings.get("password") or "")
        payload = {
            "flag": "login",
            "account": str(self.settings.get("username") or ""),
            "password": hashlib.md5(password.encode("utf-8")).hexdigest(),
        }
        if verify_code:
            payload["verifyCode"] = verify_code
        response = self.session.post(
            self._url("/public/cgi-bin/login.cgi"),
            data=payload,
            timeout=20,
        )
        data = self._parse_json(response, "登录")
        if not data.get("success"):
            raise RuntimeError(data.get("msg") or "基站 Web 登录失败。")

        self._logged_in = True
        return data

    def collect_log(
        self,
        download_dir: str | Path | None = None,
        *,
        timeout_seconds: int = 600,
        poll_interval_seconds: int = 5,
    ) -> dict[str, Any]:
        """Download the latest LogFile into the configured folder."""
        self.login()
        target_dir = Path(download_dir or self.settings.get("log_download_dir") or config.PM_ARTIFACTS_DIR)
        target_dir.mkdir(parents=True, exist_ok=True)

        log_item = self._wait_for_download_item("LogFile", timeout_seconds, poll_interval_seconds)
        remote_file = str(log_item.get("AP") or "").strip()
        if not remote_file:
            raise RuntimeError("未获取到可下载的基站日志文件。")

        local_name = self._build_local_name(remote_file)
        local_path = target_dir / local_name
        self._download_file(remote_file, local_path)
        size_bytes = local_path.stat().st_size if local_path.exists() else 0
        if size_bytes <= 0:
            raise RuntimeError("日志文件下载失败或为空。")

        return {
            "success": True,
            "remote_path": remote_file,
            "local_path": str(local_path),
            "file_size_bytes": size_bytes,
            "message": "基站日志已下载到本地。",
        }

    def start_capture(
        self,
        select_msg: str | None = None,
        transmit_ip: str | None = None,
    ) -> BaseWebCaptureSession:
        """Start basestation capture."""
        self.login()
        select_msg = str(select_msg or self.settings.get("capture_select_msg") or "CP")
        transmit_ip = str(transmit_ip if transmit_ip is not None else self.settings.get("capture_transmit_ip") or "")
        payload = {
            "types": "start",
            "SelectMsg": select_msg,
            "TransmitIp": transmit_ip,
        }
        response = self.session.post(
            self._url("/public/cgi-bin/caught.cgi"),
            json=payload,
            timeout=30,
        )
        data = self._parse_json(response, "启动抓包")
        if int(data.get("code") or 0) != 200 or not data.get("success"):
            raise RuntimeError(data.get("msg") or "基站 Web 抓包启动失败。")

        return BaseWebCaptureSession(
            select_msg=select_msg,
            transmit_ip=transmit_ip,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def stop_capture(
        self,
        session_handle: BaseWebCaptureSession,
        download_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Stop capture and download the pcap to local disk."""
        if not session_handle:
            raise RuntimeError("缺少基站抓包会话。")

        self.login()
        payload = {
            "types": "stop",
            "SelectMsg": session_handle.select_msg,
            "TransmitIp": "StopTcpdump",
        }
        response = self.session.post(
            self._url("/public/cgi-bin/caught.cgi"),
            json=payload,
            timeout=30,
        )
        data = self._parse_json(response, "停止抓包")
        if int(data.get("code") or 0) != 200 or not data.get("success"):
            raise RuntimeError(data.get("msg") or "基站 Web 抓包停止失败。")

        remote_path = str(data.get("filepath") or "").strip()
        if not remote_path:
            raise RuntimeError("抓包停止后未返回 pcap 路径。")

        target_dir = Path(
            download_dir
            or self.settings.get("capture_download_dir")
            or self.settings.get("log_download_dir")
            or config.PM_ARTIFACTS_DIR
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        local_path = target_dir / self._build_capture_name()
        fallback_from = ""
        try:
            self._download_file(remote_path, local_path)
        except PermissionError:
            fallback_from = str(target_dir)
            target_dir = Path(config.PM_ARTIFACTS_DIR)
            target_dir.mkdir(parents=True, exist_ok=True)
            local_path = target_dir / local_path.name
            self._download_file(remote_path, local_path)
        size_bytes = local_path.stat().st_size if local_path.exists() else 0
        if size_bytes <= 0:
            raise RuntimeError("抓包文件下载失败或为空。")

        result = {
            "success": True,
            "remote_path": remote_path,
            "local_path": str(local_path),
            "file_size_bytes": size_bytes,
            "message": "基站抓包已停止并下载到本地。",
        }
        if fallback_from:
            result["download_dir_fallback_from"] = fallback_from
        return result

    def _wait_for_download_item(
        self,
        file_type: str,
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> dict[str, Any]:
        deadline = time.time() + max(timeout_seconds, 1)
        last_error: str | None = None
        while time.time() < deadline:
            response = self.session.post(
                self._url("/public/cgi-bin/log.cgi"),
                data={
                    "fileType": file_type,
                    "types": "download",
                },
                timeout=30,
            )
            data = self._parse_json(response, "查询日志列表")
            code = str(data.get("code") or "")
            rows = data.get("rows") if isinstance(data.get("rows"), list) else []
            if code == "200" and rows:
                first = rows[0]
                if isinstance(first, dict) and str(first.get("AP") or "").strip() and str(first.get("AP")) != "Downloading":
                    return first
            if code and code != "202":
                last_error = data.get("msg") or f"基站日志查询失败: {code}"
            time.sleep(max(poll_interval_seconds, 1))

        raise RuntimeError(last_error or "等待基站日志生成超时。")

    def _download_file(self, remote_path: str, local_path: Path) -> None:
        response = self.session.get(
            self._url("/public/cgi-bin/download.cgi"),
            params={
                "types": "download",
                "fileName": remote_path,
            },
            timeout=120,
            stream=True,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"文件下载失败: HTTP {response.status_code}")

        content_type = response.headers.get("Content-Type", "").lower()
        if "json" in content_type:
            raise RuntimeError(self._extract_error_message(response))

        local_path.parent.mkdir(parents=True, exist_ok=True)
        with local_path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    fh.write(chunk)

    def _get_encoded_verify_code(self) -> str:
        try:
            response = self.session.post(
                self._url("/public/cgi-bin/login.cgi"),
                data={"flag": "getVerifyCode"},
                timeout=15,
            )
            data = self._parse_json(response, "获取验证码")
            raw_code = str(data.get("verifyCode") or "")
            if not raw_code:
                return ""
            return _encode_verify_code(_decode_verify_code(raw_code))
        except Exception:
            return ""

    def _parse_json(self, response: requests.Response, action: str) -> dict[str, Any]:
        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(f"{action}响应不是有效 JSON。") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"{action}响应格式不正确。")
        return data

    def _extract_error_message(self, response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                return str(data.get("msg") or data.get("message") or data.get("error") or "文件下载失败。")
        except Exception:
            pass
        return response.text.strip() or "文件下载失败。"

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _build_local_name(self, remote_file: str) -> str:
        name = Path(remote_file).name
        stamp = time.strftime("%Y%m%d_%H%M%S")
        if "." in name:
            stem = Path(name).stem
            suffix = Path(name).suffix
            if suffix == ".gz" and stem.endswith(".tar"):
                return f"{stamp}_{stem}{suffix}"
            return f"{stamp}_{stem}{suffix}"
        return f"{stamp}_{name}"

    def _build_capture_name(self) -> str:
        return f"webTcpdump_{time.strftime('%Y%m%d_%H%M%S')}.pcap"


def _decode_verify_code(value: str) -> str:
    """Decode the basestation login verify-code string used by login.js."""
    pairs = (
        value[2] + value[28],
        value[3] + value[19],
        value[1] + value[21],
        value[0] + value[7],
    )
    return "".join(chr(int(pair, 16)) for pair in pairs)


def _encode_verify_code(value: str) -> str:
    """Encode a four-character verify code in the format expected by login.cgi."""
    if len(value) != 4:
        raise ValueError("verify code must contain four characters")
    ascii_hex = [format(ord(char), "x") for char in value]
    if any(len(part) != 2 for part in ascii_hex):
        raise ValueError("verify code characters must fit in one byte")

    rng = random.SystemRandom()
    random_value = "".join(rng.choice(string.ascii_letters + string.digits) for _ in range(32))
    first, second, third, fourth = (list(part) for part in ascii_hex)
    random_value = random_value[:4] + first[0] + random_value[5:18] + first[1] + random_value[19:]
    random_value = second[0] + random_value[1:10] + second[1] + random_value[11:]
    random_value = random_value[:3] + third[0] + random_value[4:24] + third[1] + random_value[25:]
    return random_value[:1] + fourth[0] + random_value[2:26] + fourth[1] + random_value[27:]


def _decode_submitted_verify_code(value: str) -> str:
    pairs = (
        value[4] + value[18],
        value[0] + value[10],
        value[3] + value[24],
        value[1] + value[26],
    )
    return "".join(chr(int(pair, 16)) for pair in pairs)
