# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None
PY_BASE = Path(sys.base_prefix)

a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[
        (str(PY_BASE / 'DLLs' / '_tkinter.pyd'), '.'),
        (str(PY_BASE / 'DLLs' / 'tcl86t.dll'), '.'),
        (str(PY_BASE / 'DLLs' / 'tk86t.dll'), '.'),
    ],
    datas=[
        ('config.py', '.'),
        (str(PY_BASE / 'Lib' / 'tkinter'), 'tkinter'),
        (str(PY_BASE / 'tcl' / 'tcl8.6'), '_tcl_data'),
        (str(PY_BASE / 'tcl' / 'tk8.6'), '_tk_data'),
        ('scrcpy-win64-v2.0', 'scrcpy-win64-v2.0'),
    ],
    hiddenimports=[
        '_tkinter',
        'requests',
        'urllib3',
        'yaml',
        'desktop',
        'desktop.main',
        'desktop.controller',
        'desktop.state',
        'desktop.formatters',
        'desktop.case_library',
        'desktop.case_models',
        'desktop.case_templates',
        'desktop.widgets',
        'desktop.widgets.devices',
        'desktop.widgets.cases',
        'desktop.widgets.run_monitor',
        'desktop.widgets.results',
        'desktop.widgets.settings',
        'device',
        'device.device_manager',
        'device.android_device',
        'network',
        'network.network_controller',
        'network.fiveg_tester',
        'network.traffic_tester',
        'network.network_monitor',
        'pm_tests',
        'pm_tests.core',
        'pm_tests.core.adapters',
        'pm_tests.core.facade',
        'pm_tests.core.actions',
        'pm_tests.core.models',
        'pm_tests.core.orchestrator',
        'pm_tests.core.planner',
        'pm_tests.core.ports',
        'pm_tests.core.runner',
        'pm_tests.core.store',
        'pm_tests.base_ssh',
        'pm_tests.traffic_server',
        'paramiko',
        'pm_tests.packet_capture',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MobileTestPlatform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MobileTestPlatform',
)
