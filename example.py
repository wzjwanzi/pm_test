"""
使用示例脚本
演示如何使用平台 API 进行自动化测试（包含5G和灌包测试）
"""
import requests
import time

# API 基础地址
BASE_URL = "http://localhost:5000/api"


def test_5g_features(device_id):
    """5G 网络测试功能"""
    print("\n===== 5G 网络测试 =====")

    # 获取当前网络类型
    print("1. 获取当前网络类型...")
    response = requests.post(f"{BASE_URL}/5g/network-type", json={"device_id": device_id})
    result = response.json()
    print(f"   当前网络: {result.get('network_type')}")

    # 切换到 5G
    print("2. 切换到 5G 网络...")
    response = requests.post(f"{BASE_URL}/5g/switch", json={
        "device_id": device_id,
        "target_network": "5G"
    })
    print(f"   {response.json()['message']}")
    time.sleep(3)

    # 获取信号强度
    print("3. 获取信号强度...")
    response = requests.post(f"{BASE_URL}/5g/signal", json={"device_id": device_id})
    result = response.json()
    if result.get('success'):
        print(f"   信号信息: {result.get('signal_info', '未知')[:100]}...")


def test_traffic_features(device_id):
    """灌包测试功能"""
    print("\n===== 灌包测试（流量测试）=====")

    # 获取流量统计
    print("1. 获取流量统计...")
    response = requests.post(f"{BASE_URL}/traffic/stats", json={"device_id": device_id})
    result = response.json()
    if result.get('success'):
        print(f"   下载: {result['rx_mb']} MB")
        print(f"   上传: {result['tx_mb']} MB")
        print(f"   总计: {result['total_mb']} MB")

    # Ping 测试
    print("2. 执行 Ping 测试...")
    response = requests.post(f"{BASE_URL}/traffic/ping-test", json={"device_id": device_id})
    result = response.json()
    if result.get('success') and result.get('samples'):
        print(f"   Ping App 目标: {result['host']}")
        for sample in result['samples']:
            print(f"   第{sample['seq']}次: {sample['latency_ms']} ms")

    # 开始下载测试
    print("3. 启动下载测试（30秒）...")
    response = requests.post(f"{BASE_URL}/traffic/download-test", json={
        "device_id": device_id,
        "url": "http://speedtest.tele2.net/10MB.zip",
        "duration": 30
    })
    print(f"   {response.json()['message']}")


def test_network_monitor(device_id):
    """网络监控功能"""
    print("\n===== 网络监控 =====")

    # 网络速度测试
    print("1. 网络速度测试...")
    response = requests.post(f"{BASE_URL}/monitor/speed-test", json={"device_id": device_id})
    result = response.json()
    if result.get('success'):
        print(f"   网络速度: {result['speed_mbps']} Mbps")

    # 连通性测试
    print("2. 连通性测试...")
    response = requests.post(f"{BASE_URL}/monitor/connectivity", json={"device_id": device_id})
    result = response.json()
    if result.get('success'):
        for host, info in result['results'].items():
            status = "✓" if info['reachable'] else "✗"
            print(f"   {status} {host}: {info.get('packet_loss', 'N/A')}")

    # 获取基站信息
    print("3. 获取基站信息...")
    response = requests.post(f"{BASE_URL}/monitor/cell-info", json={"device_id": device_id})
    result = response.json()
    if result.get('success'):
        print(f"   基站信息: {result.get('cell_info', '未知')[:100]}...")


def example_workflow():
    """完整的测试工作流示例"""

    # 1. 获取设备列表
    print("===== 移动设备自动化测试平台 - 完整示例 =====\n")
    print("1. 获取设备列表...")
    response = requests.get(f"{BASE_URL}/devices")
    devices = response.json()['devices']
    print(f"   找到设备: {devices}")

    if not devices:
        print("   没有找到设备，请连接设备后重试")
        return

    device_id = devices[0]
    print(f"   使用设备: {device_id}")

    # 2. 连接设备
    print("\n2. 连接设备...")
    response = requests.post(f"{BASE_URL}/device/connect", json={
        "device_id": device_id,
        "app_package": "com.android.browser",  # 示例：浏览器应用
        "app_activity": ".BrowserActivity"
    })
    print(f"   {response.json()['message']}")
    time.sleep(2)

    # 3. 运行 5G 网络测试
    test_5g_features(device_id)

    # 4. 运行灌包测试
    test_traffic_features(device_id)

    # 5. 运行网络监控
    test_network_monitor(device_id)

    # 6. 设置网络代理
    print("\n===== 网络代理测试 =====")
    print("1. 设置网络代理...")
    response = requests.post(f"{BASE_URL}/network/proxy", json={
        "device_id": device_id,
        "proxy_host": "192.168.1.1",
        "proxy_port": 8080
    })
    print(f"   {response.json()['message']}")

    # 7. 执行搜索操作
    print("2. 执行搜索...")
    response = requests.post(f"{BASE_URL}/device/search", json={
        "device_id": device_id,
        "search_text": "自动化测试"
    })
    print(f"   {response.json()['message']}")

    # 8. 断开设备
    print("\n===== 清理 =====")
    print("断开设备连接...")
    response = requests.post(f"{BASE_URL}/device/disconnect", json={
        "device_id": device_id
    })
    print(f"   {response.json()['message']}")

    print("\n✅ 所有测试完成！")


if __name__ == "__main__":
    try:
        example_workflow()
    except Exception as e:
        print(f"❌ 错误: {e}")
