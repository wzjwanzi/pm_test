# 5G 入网测试和灌包测试指南

## 功能概述

本平台提供完整的5G网络测试和流量测试（灌包测试）功能，适用于移动设备的网络性能评估。

## 5G 网络测试

### 功能列表

1. **网络类型检测**
   - 自动识别当前网络类型（5G/4G/3G）
   - 实时显示网络状态

2. **网络切换**
   - 支持 4G/5G 网络切换
   - 自动验证切换结果

3. **信号强度监控**
   - 获取实时信号强度信息
   - 显示详细的信号参数

4. **基站信息**
   - 查看当前连接的基站信息
   - 获取小区 ID 和频段信息

### API 接口

#### 1. 获取网络类型
```bash
POST /api/5g/network-type
{
    "device_id": "设备ID"
}
```

#### 2. 切换网络
```bash
POST /api/5g/switch
{
    "device_id": "设备ID",
    "target_network": "5G"  # 或 "4G"
}
```

#### 3. 获取信号强度
```bash
POST /api/5g/signal
{
    "device_id": "设备ID"
}
```

### 使用示例

```python
import requests

BASE_URL = "http://localhost:5000/api"
device_id = "your_device_id"

# 获取当前网络类型
response = requests.post(f"{BASE_URL}/5g/network-type",
    json={"device_id": device_id})
print(response.json())

# 切换到 5G
response = requests.post(f"{BASE_URL}/5g/switch",
    json={"device_id": device_id, "target_network": "5G"})
print(response.json())
```

## 灌包测试（流量测试）

### 功能列表

1. **流量统计**
   - 实时查看上传/下载流量
   - 显示总流量使用情况

2. **下载测试**
   - 持续下载测试文件
   - 可自定义测试时长和 URL
   - 适用于网络稳定性测试

3. **上传测试**
   - 持续上传数据
   - 可自定义文件大小和测试时长

4. **Ping 测试**
   - 测试网络延迟
   - 统计最小/平均/最大延迟
   - 计算丢包率

5. **速度测试**
   - 测量实际下载速度
   - 以 Mbps 为单位显示结果

### API 接口

#### 1. 获取流量统计
```bash
POST /api/traffic/stats
{
    "device_id": "设备ID"
}
```

响应示例：
```json
{
    "success": true,
    "rx_mb": 1234.56,
    "tx_mb": 567.89,
    "total_mb": 1802.45
}
```

#### 2. 开始下载测试
```bash
POST /api/traffic/download-test
{
    "device_id": "设备ID",
    "url": "http://speedtest.tele2.net/100MB.zip",
    "duration": 60
}
```

#### 3. Ping 测试
```bash
POST /api/traffic/ping-test
{
    "device_id": "设备ID",
    "host": "8.8.8.8",
    "count": 50
}
```

响应示例：
```json
{
    "success": true,
    "host": "8.8.8.8",
    "count": 50,
    "stats": {
        "min_ms": 12.5,
        "avg_ms": 25.3,
        "max_ms": 45.8,
        "mdev_ms": 8.2
    }
}
```

#### 4. 速度测试
```bash
POST /api/monitor/speed-test
{
    "device_id": "设备ID",
    "test_url": "http://speedtest.tele2.net/10MB.zip"
}
```

响应示例：
```json
{
    "success": true,
    "speed_mbps": 85.6,
    "duration_seconds": 2.3
}
```

### 使用示例

```python
import requests

BASE_URL = "http://localhost:5000/api"
device_id = "your_device_id"

# 获取流量统计
response = requests.post(f"{BASE_URL}/traffic/stats",
    json={"device_id": device_id})
stats = response.json()
print(f"下载: {stats['rx_mb']} MB, 上传: {stats['tx_mb']} MB")

# 开始下载测试（60秒）
response = requests.post(f"{BASE_URL}/traffic/download-test",
    json={
        "device_id": device_id,
        "url": "http://speedtest.tele2.net/100MB.zip",
        "duration": 60
    })
print(response.json())

# Ping 测试
response = requests.post(f"{BASE_URL}/traffic/ping-test",
    json={
        "device_id": device_id,
        "host": "8.8.8.8",
        "count": 50
    })
result = response.json()
if result['success']:
    print(f"平均延迟: {result['stats']['avg_ms']} ms")
```

## 网络监控

### 功能列表

1. **网络信息**
   - 获取完整的网络配置信息
   - 显示 IP 地址、WiFi 信息等

2. **连通性测试**
   - 测试多个主机的连通性
   - 显示丢包率

3. **基站信息**
   - 获取当前基站详细信息
   - 显示服务状态

### API 接口

#### 1. 获取网络信息
```bash
POST /api/monitor/network-info
{
    "device_id": "设备ID"
}
```

#### 2. 连通性测试
```bash
POST /api/monitor/connectivity
{
    "device_id": "设备ID",
    "hosts": ["8.8.8.8", "1.1.1.1", "baidu.com"]
}
```

#### 3. 获取基站信息
```bash
POST /api/monitor/cell-info
{
    "device_id": "设备ID"
}
```

## 测试场景示例

### 场景1：5G 网络稳定性测试

```python
# 1. 切换到 5G
switch_to_5g(device_id)

# 2. 持续下载测试（5分钟）
start_download_test(device_id, duration=300)

# 3. 每30秒检查一次流量和信号
for i in range(10):
    time.sleep(30)
    get_traffic_stats(device_id)
    get_signal_strength(device_id)
```

### 场景2：网络切换测试

```python
# 1. 在 5G 下测试
switch_to_5g(device_id)
speed_test(device_id)
ping_test(device_id)

# 2. 切换到 4G 测试
switch_to_4g(device_id)
speed_test(device_id)
ping_test(device_id)

# 3. 对比结果
```

### 场景3：大流量灌包测试

```python
# 1. 记录初始流量
initial_stats = get_traffic_stats(device_id)

# 2. 启动持续下载（10分钟）
start_download_test(device_id,
    url="http://speedtest.tele2.net/1GB.zip",
    duration=600)

# 3. 监控流量变化
time.sleep(600)
final_stats = get_traffic_stats(device_id)

# 4. 计算流量增量
traffic_used = final_stats['total_mb'] - initial_stats['total_mb']
print(f"测试期间使用流量: {traffic_used} MB")
```

## 注意事项

1. **权限要求**
   - 某些功能需要设备 root 权限
   - 网络切换需要系统级权限

2. **测试建议**
   - 长时间测试建议使用无限流量套餐
   - 注意设备发热和电量消耗
   - 建议在稳定的测试环境中进行

3. **数据安全**
   - 测试 URL 应使用可信的测试服务器
   - 避免在生产环境中进行大流量测试

4. **结果分析**
   - 多次测试取平均值更准确
   - 注意记录测试时的环境因素（位置、时间等）
   - 对比不同网络类型的性能差异

## 故障排查

### 问题1：无法切换到 5G
- 检查设备是否支持 5G
- 确认 SIM 卡已开通 5G 服务
- 检查当前位置是否有 5G 信号覆盖

### 问题2：下载测试无响应
- 检查测试 URL 是否可访问
- 确认设备网络连接正常
- 查看 ADB 日志排查错误

### 问题3：Ping 测试超时
- 检查目标主机是否可达
- 确认设备防火墙设置
- 尝试更换测试主机

## 推荐测试服务器

- **Tele2 SpeedTest**: http://speedtest.tele2.net/
  - 提供多种大小的测试文件（1MB - 1GB）

- **Google DNS**: 8.8.8.8
  - 适合 Ping 测试

- **Cloudflare DNS**: 1.1.1.1
  - 低延迟，适合连通性测试
