# User Quick Start

## Start From Source

```powershell
cd D:\test\mobile_automation_platform
python desktop_app.py
```

The desktop app opens the Tkinter workbench.

## Start From Packaged Build

For the phase 4 delivery build:

```powershell
D:\test\mobile_automation_platform\release_phase4\MobileTestPlatform\MobileTestPlatform.exe
```

## Basic Workflow

1. Connect an Android device and enable USB debugging.
2. Click **刷新设备**.
3. Select the device.
4. Click **执行预检**.
5. Pick an operation template.
6. Click **添加用例**.
7. Click **开始执行**.
8. Watch the task status and step table.
9. Inspect result details and raw JSON on the right side.

## Verification Commands

Run local verification:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_dev.ps1
```

Run package verification:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe
```
