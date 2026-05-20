"""网络质量监控模块。"""
import time
from datetime import datetime
from typing import Dict, List

from network.network_utils import (
    get_active_interface,
    get_connectivity_dump,
    get_interface_ip_info,
    get_interface_stats,
    parse_bandwidth_from_connectivity,
)
from utils.adb_utils import adb_shell, adb_shell_script, command_exists


class NetworkMonitor:
    """网络质量监控类。"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.monitoring = False
        self.last_error = ""

    def get_network_info(self) -> Dict:
        """获取完整的网络信息。"""
        try:
            telephony_result = adb_shell(
                self.device_id,
                ["dumpsys", "telephony.registry"],
                check=True,
                timeout=20,
            )
            wifi_result = adb_shell(self.device_id, ["dumpsys", "wifi"], timeout=20)
            active_interface = get_active_interface(self.device_id)
            ip_info = get_interface_ip_info(self.device_id, active_interface.name)
            connectivity_dump = get_connectivity_dump(self.device_id)
            bandwidth = parse_bandwidth_from_connectivity(connectivity_dump, active_interface.name) or {}

            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "interface": active_interface.name,
                "rx_bytes": active_interface.rx_bytes,
                "tx_bytes": active_interface.tx_bytes,
                "network_type": telephony_result.stdout.strip(),
                "ip_info": ip_info.strip(),
                "wifi_info": wifi_result.stdout.strip(),
                "bandwidth_hint": bandwidth,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc)
            }

    def test_network_speed(self, test_url: str = "http://speedtest.tele2.net/10MB.zip") -> Dict:
        """测试网络速度。"""
        try:
            if not command_exists(self.device_id, "curl") and not command_exists(self.device_id, "wget"):
                raise RuntimeError("当前设备缺少 curl/wget，无法执行真实下载测速。")

            active_interface = get_active_interface(self.device_id)
            before_stats = {item.name: item for item in get_interface_stats(self.device_id)}
            start_time = time.time()
            if command_exists(self.device_id, "curl"):
                adb_shell_script(
                    self.device_id,
                    f"curl -L -o /dev/null '{test_url}'",
                    check=True,
                    timeout=30,
                )
            else:
                adb_shell_script(
                    self.device_id,
                    f"wget -O /dev/null '{test_url}'",
                    check=True,
                    timeout=30,
                )
            end_time = time.time()
            duration = max(end_time - start_time, 0.001)

            after_stats = {item.name: item for item in get_interface_stats(self.device_id)}
            before = before_stats.get(active_interface.name)
            after = after_stats.get(active_interface.name)
            if not before or not after:
                raise RuntimeError("测速后未能重新读取活跃网络接口。")

            downloaded_bytes = max(after.rx_bytes - before.rx_bytes, 0)
            if downloaded_bytes == 0:
                raise RuntimeError("测速期间未观察到下载流量变化。")

            speed_bytes = downloaded_bytes / duration
            speed_mbps = (speed_bytes * 8) / (1024 * 1024)

            return {
                "success": True,
                "speed_mbps": round(speed_mbps, 2),
                "speed_bytes_per_sec": round(speed_bytes, 2),
                "duration_seconds": round(duration, 2),
                "test_url": test_url,
                "interface": active_interface.name,
                "mode": "measured",
            }
        except Exception as exc:
            try:
                active_interface = get_active_interface(self.device_id)
                connectivity_dump = get_connectivity_dump(self.device_id)
                bandwidth = parse_bandwidth_from_connectivity(connectivity_dump, active_interface.name)
                if bandwidth:
                    return {
                        "success": True,
                        "speed_mbps": bandwidth["down_mbps"],
                        "upload_mbps": bandwidth["up_mbps"],
                        "duration_seconds": 0,
                        "test_url": test_url,
                        "interface": active_interface.name,
                        "mode": "estimated",
                        "note": f"设备缺少 curl/wget，返回系统带宽估算值。原始测速失败原因: {exc}",
                    }
            except Exception:
                pass

            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc)
            }

    def check_connectivity(self, hosts: List[str] = None) -> Dict:
        """检查网络连通性。"""
        if hosts is None:
            hosts = ["8.8.8.8", "1.1.1.1", "baidu.com"]

        results = {}
        for host in hosts:
            try:
                result = adb_shell(
                    self.device_id,
                    ["ping", "-c", 3, "-W", 2, host],
                    timeout=12,
                )

                success = result.returncode == 0
                packet_loss = "100%"

                if success:
                    for line in result.stdout.split('\n'):
                        if 'packet loss' in line or '丢包' in line:
                            parts = line.split(',')
                            for part in parts:
                                if '%' in part and ('loss' in part or '丢包' in part):
                                    packet_loss = part.strip().split()[0]

                results[host] = {
                    "reachable": success,
                    "packet_loss": packet_loss
                }
            except Exception as exc:
                results[host] = {
                    "reachable": False,
                    "error": str(exc)
                }

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }

    def get_cell_info(self) -> Dict:
        """获取基站信息。"""
        try:
            result = adb_shell(
                self.device_id,
                ["dumpsys", "telephony.registry"],
                check=True,
                timeout=20,
            )
            cell_lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if "mCellInfo=" in line or "mServiceState=" in line
            ]

            return {
                "success": True,
                "cell_info": "\n".join(cell_lines)
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "error": str(exc)
            }
