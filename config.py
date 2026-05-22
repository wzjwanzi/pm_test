"""项目配置。"""

import sys
from pathlib import Path


if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Runtime data
RUNTIME_DATA_DIR = BASE_DIR
SETTINGS_FILE = RUNTIME_DATA_DIR / 'settings.json'
CASES_DIR = RUNTIME_DATA_DIR / 'cases'

# 网络代理配置
PROXY_HOST = '0.0.0.0'
PROXY_PORT = 8080

# 设备配置
# 启动预读配置
STARTUP_INDEX_DIR = r'D:\test\index'
STARTUP_PRIORITY_RULE_FILES = [
    'UTF8_READ_GUIDELINES.md',
    'AUTO_MD_READ_RULES.md',
]

# Ping app fixed test configuration
PING_APP_PACKAGE = 'com.lipinic.ping'
PING_APP_ACTIVITY = '.MainActivity'
PING_APP_HOST_RESOURCE_ID = 'com.lipinic.ping:id/editTextHost'
PING_APP_START_BUTTON_RESOURCE_ID = 'com.lipinic.ping:id/btnStart'
PING_APP_RESULT_RESOURCE_ID = 'com.lipinic.ping:id/txtResult'
PING_APP_FIXED_HOST = '10.88.149.164'
PING_APP_FIXED_COUNT = 5
PING_APP_LAUNCH_WAIT_SECONDS = 2
PING_APP_CAPTURE_WAIT_SECONDS = 28
PING_APP_BACKSPACE_COUNT = 15

# Device iperf3 fixed uplink test configuration
MAGIC_IPERF_PACKAGE = 'com.nextdoordeveloper.miperf.miperf'
MAGIC_IPERF_ACTIVITY = '.MainActivity'
MAGIC_IPERF_WIZARD_BUTTON_ID = 'com.nextdoordeveloper.miperf.miperf:id/bnWizard'
MAGIC_IPERF_RUN_BUTTON_ID = 'com.nextdoordeveloper.miperf.miperf:id/bnRun'
MAGIC_IPERF_RESULT_ID = 'com.nextdoordeveloper.miperf.miperf:id/tvResult'
MAGIC_IPERF_COMMAND_ID = 'com.nextdoordeveloper.miperf.miperf:id/etCommand'
MAGIC_IPERF_HISTORY_COMMAND = 'iperf -u -c 10.88.149.164 -b 120m -t 60000 -i 1 -l 1350 -p 6087'
MAGIC_IPERF_RESULT_WAIT_SECONDS = 2
MAGIC_IPERF_APK_PATH = 'magic_iperf.apk'
MAGIC_IPERF_BINARY_ENTRY = 'res/raw/iperf'
MAGIC_IPERF_LOCAL_BINARY = 'magic_iperf_iperf2.bin'
MAGIC_IPERF_DEVICE_BINARY = '/data/local/tmp/magic_iperf2'
MAGIC_IPERF_DEVICE_LOG = '/sdcard/magic_iperf_uplink.log'
MAGIC_IPERF_STATUS_TAIL_LINES = 20
MAGIC_IPERF_ARGUMENTS = '-u -c 10.88.149.164 -b 120m -t 60000 -i 1 -l 1350 -p 6087'
DEVICE_IPERF3_BINARY = '/data/local/tmp/iperf3'
DEVICE_IPERF3_LOG = '/sdcard/iperf3_uplink.log'
DEVICE_IPERF3_STATUS_TAIL_LINES = 20
DEVICE_IPERF_BINARY = '/data/local/tmp/iperf'
DEVICE_IPERF_LOG = '/sdcard/iperf_uplink.log'

DEFAULT_RUNTIME_SETTINGS = {
    "base_web": {
        "host": "192.168.13.236",
        "port": 8400,
        "username": "root",
        "password": "5GNR@root",
        "log_download_dir": r"D:\test\autopm_system\log",
        "capture_select_msg": "CP",
        "capture_transmit_ip": "",
        "capture_download_dir": r"D:\test\autopm_system\log",
        "capture_signal_enabled": True,
        "capture_data_enabled": False,
        "capture_fapi_interface": "FAPI1",
    },
    "ssh": {
        "host": "192.168.13.236",
        "port": 22,
        "username": "root",
        "password": "Root@236_",
        "log_output_dir": r"D:\test\autopm_system\log",
        "log_command": "",
        "rlc_up_log_command": "while true; do odi -n duapp0 dump-rlc-om-info; odi -n duapp0 display-mac-non-zero-om 1; odi -n duapp0 display-mac-non-zero-om 2; odi -n upapp net-stat; date; sleep 1; done",
        "rate_log_command": "numOfDuapp=`ps -ef | grep mac_phy_intf | grep duapp | wc -l`; while true; do clear; for ((i=0;i<$numOfDuapp;i++)); do odi -q -n duapp$i show-mac-throughput-count 5; done; date; sleep 2; done",
        "cpu_log_command": "while true; do top -b -n 1 | head -n 9; date; sleep 1; done",
        "rrc_release_command": "odi -n duapp0 display-ue-info | grep Crnti | awk '{print $3}' | xargs -r -I {} sh -c 'odi -n duapp0 release-ue {}'",
        "rrc_release_count": 8,
        "rrc_release_interval_seconds": 5,
        "force_rlc_escape_command": "odi -n duapp0 display-ue-info | grep Super | awk '{print $3}' | xargs -r -I {} sh -c 'odi -n duapp0 force-rlc-escape-ctrl 1 {}'",
        "force_rlc_escape_count": 3,
        "force_rlc_escape_interval_seconds": 5,
        "connect_timeout": 20,
    },
    "ping": {
        "host": PING_APP_FIXED_HOST,
        "count": PING_APP_FIXED_COUNT,
    },
    "common": {
        "delay_seconds": 5,
    },
    "iperf": {
        "tool": "iperf",
        "host": "10.88.149.164",
        "port": 6087,
        "bandwidth": "120m",
        "duration": 60000,
        "interval": 1,
        "packet_len": 1350,
        "protocol": "udp",
    },
    "traffic": {
        "server_host": "10.88.149.164",
        "server_port": 22,
        "server_username": "root",
        "server_password": "Root@164_",
        "server_connect_timeout": 20,
        "server_log_dir": r"D:\test\autopm_system\log",
        "server_downlink_target": "10.6.251.27",
        "server_downlink_port": 6011,
        "server_downlink_bandwidth": "250m",
        "server_downlink_duration": 60000,
        "server_downlink_packet_len": 1300,
        "server_uplink_listen_port": 7011,
        "server_ping_target": "10.6.251.27",
        "server_ping_count": 5,
        "phone_uplink_target": "10.88.149.164",
        "phone_uplink_port": 7011,
        "phone_uplink_bandwidth": "120m",
        "phone_uplink_duration": 6000,
        "phone_uplink_packet_len": 1350,
        "phone_downlink_listen_port": 6011,
        "phone_ping_target": "10.88.149.164",
        "device_overrides": {},
    },
}

# Downlink monitoring configuration
TRAFFIC_MONITOR_SAMPLE_SECONDS = 1.0

# PM test platform configuration
PM_ARTIFACTS_DIR = RUNTIME_DATA_DIR / 'artifacts' / 'test_runs'
PACKET_CAPTURE_INTERFACE = 'any'
PACKET_CAPTURE_DEVICE_DIR = '/sdcard/pm_packet_captures'
PACKET_CAPTURE_BINARY_CANDIDATES = [
    'tcpdump',
    '/data/local/tmp/tcpdump',
    '/system/bin/tcpdump',
    '/system/xbin/tcpdump',
]
PACKET_CAPTURE_START_WAIT_SECONDS = 1.0
PACKET_CAPTURE_STOP_WAIT_SECONDS = 1.0
