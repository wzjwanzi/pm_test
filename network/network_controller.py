"""网络控制模块。"""
import time

from utils.adb_utils import adb_shell


class NetworkController:
    """控制设备网络连接。"""

    def __init__(self):
        self.proxy_process = None
        self.last_error = ""

    def enable_network(self, device_id: str) -> bool:
        """启用设备网络。"""
        try:
            adb_shell(device_id, ["svc", "wifi", "enable"], check=True)
            adb_shell(device_id, ["svc", "data", "enable"], check=True)
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"启用网络失败: {exc}")
            return False

    def disable_network(self, device_id: str) -> bool:
        """禁用设备网络。"""
        try:
            adb_shell(device_id, ["svc", "wifi", "disable"], check=True)
            adb_shell(device_id, ["svc", "data", "disable"], check=True)
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"禁用网络失败: {exc}")
            return False

    def set_proxy(self, device_id: str, proxy_host: str, proxy_port: int) -> bool:
        """设置设备代理。"""
        try:
            adb_shell(device_id, ["settings", "put", "global", "http_proxy", f"{proxy_host}:{proxy_port}"], check=True)
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"设置代理失败: {exc}")
            return False

    def toggle_airplane_mode(self, device_id: str, wait_seconds: float = 1.0) -> bool:
        """Toggle airplane mode once to force network re-attach."""
        try:
            adb_shell(
                device_id,
                ["cmd", "connectivity", "airplane-mode", "enable"],
                check=True,
                timeout=15,
            )
            time.sleep(wait_seconds)
            adb_shell(
                device_id,
                ["cmd", "connectivity", "airplane-mode", "disable"],
                check=True,
                timeout=15,
            )
            self.last_error = ""
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"飞行模式切换失败: {exc}")
            return False
