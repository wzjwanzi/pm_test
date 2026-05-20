"""5G 网络测试模块。"""
import time
from typing import Dict

from utils.adb_utils import adb_shell, adb_shell_text


FIVE_G_ALLOWED_NETWORK_TYPES = "11001111101111111111"
FOUR_G_ALLOWED_NETWORK_TYPES = "01001111101111111111"


class FiveGTester:
    """5G 网络测试类。"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.last_error = ""

    def get_network_type(self) -> str:
        """获取当前网络类型。"""
        try:
            telephony_dump = adb_shell_text(
                self.device_id,
                ["dumpsys", "telephony.registry"],
                check=True,
                timeout=20,
            )

            if "accessNetworkTechnology=NR" in telephony_dump or "getRilDataRadioTechnology=20(NR" in telephony_dump:
                return "5G"
            if "accessNetworkTechnology=LTE" in telephony_dump or "getRilDataRadioTechnology=14(LTE)" in telephony_dump:
                return "4G"
            if any(keyword in telephony_dump for keyword in ("HSPA", "UMTS", "WCDMA", "TD_SCDMA")):
                return "3G"
            if any(keyword in telephony_dump for keyword in ("EDGE", "GPRS", "GSM")):
                return "2G"
            return "Unknown"
        except Exception as exc:
            self.last_error = str(exc)
            return f"Error: {exc}"

    def switch_to_5g(self) -> bool:
        """切换到 5G 允许网络集合。"""
        try:
            adb_shell(
                self.device_id,
                ["cmd", "phone", "set-allowed-network-types-for-users", FIVE_G_ALLOWED_NETWORK_TYPES],
                check=True,
                timeout=20,
            )
            self.last_error = ""
            time.sleep(2)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"切换 5G 失败: {exc}")
            return False

    def switch_to_4g(self) -> bool:
        """切换到 4G 允许网络集合。"""
        try:
            adb_shell(
                self.device_id,
                ["cmd", "phone", "set-allowed-network-types-for-users", FOUR_G_ALLOWED_NETWORK_TYPES],
                check=True,
                timeout=20,
            )
            self.last_error = ""
            time.sleep(2)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            print(f"切换 4G 失败: {exc}")
            return False

    def get_signal_strength(self) -> Dict:
        """获取信号强度。"""
        try:
            telephony_dump = adb_shell_text(
                self.device_id,
                ["dumpsys", "telephony.registry"],
                check=True,
                timeout=20,
            )
            signal_line = ""
            for line in telephony_dump.splitlines():
                if "mSignalStrength=" in line:
                    signal_line = line.strip()
                    break

            return {
                "success": True,
                "signal_info": signal_line or "未读取到信号信息"
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc)
            }

