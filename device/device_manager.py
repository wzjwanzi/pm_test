"""Device management through ADB only."""
from __future__ import annotations

from typing import List

from .android_device import AndroidDevice
from utils.adb_utils import adb_shell, get_connected_devices


class DeviceManager:
    """Manage Android devices connected through ADB."""

    def __init__(self):
        self.devices: dict[str, AndroidDevice] = {}
        self.last_error = ""

    def get_connected_devices(self) -> List[str]:
        """Return all online ADB devices."""
        try:
            self.last_error = ""
            return get_connected_devices()
        except Exception as exc:
            self.last_error = str(exc)
            print(f"Failed to get device list: {exc}")
            return []

    def connect_device(
        self,
        device_id: str,
        app_package: str | None = None,
        app_activity: str | None = None,
    ) -> AndroidDevice:
        """Register an ADB-backed device and optionally launch an app."""
        if not device_id:
            raise RuntimeError("Missing device ID.")

        online_devices = self.get_connected_devices()
        if device_id not in online_devices:
            raise RuntimeError(f"Device is not online through ADB: {device_id}")

        device = AndroidDevice(device_id)
        self.devices[device_id] = device

        if app_package:
            self.launch_app(device_id, app_package, app_activity)

        return device

    def disconnect_device(self, device_id: str):
        """Forget a device from the in-process registry.

        ADB itself is stateless here, so this does not stop or reset the device.
        """
        self.devices.pop(device_id, None)

    def launch_app(self, device_id: str, app_package: str, app_activity: str | None = None):
        """Launch an app with adb shell."""
        if not device_id:
            raise RuntimeError("Missing device ID.")
        if not app_package:
            raise RuntimeError("Missing app package.")

        self.last_error = ""
        try:
            if app_activity:
                result = adb_shell(
                    device_id,
                    ["am", "start", "-n", f"{app_package}/{app_activity}"],
                    check=True,
                    timeout=20,
                )
            else:
                result = adb_shell(
                    device_id,
                    ["monkey", "-p", app_package, "-c", "android.intent.category.LAUNCHER", "1"],
                    check=True,
                    timeout=20,
                )
            return result.stdout.strip()
        except Exception as exc:
            self.last_error = str(exc)
            raise RuntimeError(f"Failed to launch app through ADB: {exc}") from exc

    def get_device(self, device_id: str) -> AndroidDevice | None:
        """Return an ADB-backed device object.

        If the caller has not explicitly connected first, create a lightweight
        wrapper as long as the device is currently online.
        """
        if device_id in self.devices:
            return self.devices[device_id]

        if device_id and device_id in self.get_connected_devices():
            self.devices[device_id] = AndroidDevice(device_id)
            return self.devices[device_id]

        return None
