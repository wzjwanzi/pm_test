# 移动设备自动化测试平台

一个功能强大的移动设备自动化测试平台，支持设备控制、网络管理、5G测试和灌包测试。

## 主要功能

### 📱 设备管理
- 自动检测连接的 Android/iOS 设备
- 远程控制设备应用
- 自动化操作（搜索、点击等）

### 🌐 网络控制
- 启用/禁用设备网络
- 设置网络代理
- 模拟各种网络环境

### 📡 5G 网络测试
- 网络类型检测（5G/4G/3G）
- 4G/5G 网络切换
- 信号强度监控
- 基站信息获取

### 🚀 灌包测试（流量测试）
- 实时流量统计
- 持续下载/上传测试
- Ping 测试（延迟和丢包率）
- 网络速度测试

### 📊 网络监控
- 完整网络信息
- 多主机连通性测试
- 网络质量评估

## 快速开始

### 方式一：使用打包的 exe 文件（推荐）

1. 下载 release 包
2. 确保已安装 Appium 和 ADB
3. 启动 Appium 服务：`appium`
4. 双击 `start.bat` 或运行 `MobileTestPlatform.exe`
5. 浏览器访问 `http://localhost:5000`

### 方式二：从源码运行

1. 安装依赖：`pip install -r requirements.txt`
2. 启动 Appium：`appium`
3. 启动平台：`python app.py`
4. 访问 `http://localhost:5000`

## 打包部署

### Windows 打包
```bash
# 自动打包
build.bat

# 或快速打包
quick_build.bat
```

### Linux/macOS 打包
```bash
chmod +x build.sh
./build.sh
```

详细说明请查看 [BUILD_GUIDE.md](BUILD_GUIDE.md)

## 文档

- [使用指南](USAGE.md) - 详细的使用说明
- [5G测试指南](5G_TESTING_GUIDE.md) - 5G和灌包测试详细说明
- [打包指南](BUILD_GUIDE.md) - 打包部署完整指南

## 技术栈

- Python 3.8+ / Flask
- Appium + Selenium
- mitmproxy + ADB
- PyInstaller
