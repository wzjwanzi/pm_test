# 使用指南

## 环境准备

### 1. 安装 Python 依赖
```bash
pip install -r requirements.txt
```

### 2. 安装 Appium
```bash
npm install -g appium
npm install -g appium-doctor

# 安装 UiAutomator2 驱动（Android）
appium driver install uiautomator2
```

### 3. 安装 ADB（Android Debug Bridge）
- 下载 Android SDK Platform Tools
- 将 ADB 添加到系统环境变量

### 4. 配置手机
- 开启开发者选项
- 启用 USB 调试
- 通过 USB 连接手机到电脑

## 启动平台

### 1. 启动 Appium 服务
```bash
appium
```

### 2. 启动平台
```bash
python app.py
```

### 3. 访问 Web 界面
打开浏览器访问：http://localhost:5000

## 使用方法

### Web 界面操作

1. **设备管理**
   - 点击"刷新设备列表"查看连接的设备
   - 点击设备卡片选择要操作的设备

2. **连接设备**
   - 输入应用包名和 Activity（可选）
   - 点击"连接设备"建立连接

3. **网络控制**
   - 启用/禁用网络：控制设备的 WiFi 和移动数据
   - 设置代理：配置设备通过指定代理访问网络

4. **自动化操作**
   - 输入搜索内容
   - 可选：指定搜索框和按钮的 ID
   - 点击"执行搜索"

### API 调用

参考 `example.py` 文件，使用 Python 脚本调用 API：

```python
import requests

# 获取设备列表
response = requests.get("http://localhost:5000/api/devices")
devices = response.json()['devices']

# 连接设备
requests.post("http://localhost:5000/api/device/connect", json={
    "device_id": "your_device_id",
    "app_package": "com.example.app"
})

# 执行搜索
requests.post("http://localhost:5000/api/device/search", json={
    "device_id": "your_device_id",
    "search_text": "搜索内容"
})
```

## 常见问题

### 1. 找不到设备
- 确认手机已连接并开启 USB 调试
- 运行 `adb devices` 检查设备是否被识别
- 检查 USB 驱动是否正确安装

### 2. Appium 连接失败
- 确认 Appium 服务已启动
- 检查端口 4723 是否被占用
- 查看 Appium 日志排查错误

### 3. 无法找到搜索框
- 使用 Appium Inspector 查看应用元素
- 获取正确的元素 ID 或 XPath
- 在 Web 界面中指定搜索框 ID

### 4. 网络控制不生效
- 确认设备已 root 或具有相应权限
- 某些设备可能需要额外的权限设置

## 高级功能

### 获取应用包名和 Activity

```bash
# 查看当前运行的应用
adb shell dumpsys window | grep mCurrentFocus

# 列出所有已安装应用
adb shell pm list packages
```

### 使用 Appium Inspector

1. 启动 Appium Desktop
2. 配置 Desired Capabilities
3. 启动 Inspector 查看应用元素结构
4. 获取元素的 ID、XPath 等定位信息

## 扩展开发

平台采用模块化设计，可以轻松扩展功能：

- `device/` - 添加更多设备操作方法
- `network/` - 扩展网络控制功能
- `app.py` - 添加新的 API 接口
- `templates/` - 自定义 Web 界面
