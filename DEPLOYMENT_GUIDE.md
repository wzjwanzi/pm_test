# 完整部署指南

## 当前状态

✅ 平台功能已完成
- 设备管理
- 网络控制
- 5G 网络测试
- 灌包测试
- 网络监控

⚠️ 打包问题
- 当前系统：Python 3.14.0a1（开发版）
- PyInstaller 不支持此版本
- 需要 Python 3.11 或 3.12 进行打包

## 解决方案

### 方案一：安装 Python 3.11 并打包（推荐）

#### 步骤 1：下载 Python 3.11

**直接下载链接（Windows 64位）：**
```
https://www.python.org/ftp/python/3.11.10/python-3.11.10-amd64.exe
```

或访问官网：https://www.python.org/downloads/

#### 步骤 2：安装 Python 3.11

1. 运行下载的安装程序
2. **重要**：勾选 "Add Python 3.11 to PATH"
3. 点击 "Install Now" 或 "Customize installation"
4. 等待安装完成

#### 步骤 3：验证安装

打开**新的**命令行窗口：
```bash
py --list
```

应该看到：
```
-3.14-64  *
-3.11-64
```

测试 Python 3.11：
```bash
py -3.11 --version
```

#### 步骤 4：使用 Python 3.11 打包

```bash
# 进入项目目录
cd D:\test\mobile_automation_platform

# 运行打包脚本
build_with_py311.bat
```

或手动执行：
```bash
# 安装依赖
py -3.11 -m pip install -r requirements.txt

# 执行打包
py -3.11 -m PyInstaller build.spec --clean

# 打包完成后，exe 文件在 dist 目录
```

### 方案二：直接运行源码（无需打包）

如果暂时不想安装 Python 3.11，可以直接运行：

```bash
# 进入项目目录
cd D:\test\mobile_automation_platform

# 双击运行
run.bat

# 或命令行运行
python app.py
```

访问：http://localhost:5000

## 使用前准备

### 必需组件

#### 1. Appium Server

```bash
# 安装 Node.js（如果没有）
# 下载：https://nodejs.org/

# 安装 Appium
npm install -g appium

# 安装 UiAutomator2 驱动
appium driver install uiautomator2

# 启动 Appium
appium
```

#### 2. ADB (Android Debug Bridge)

1. 下载 Android SDK Platform Tools
   - 官网：https://developer.android.com/tools/releases/platform-tools
   - 直接下载：https://dl.google.com/android/repository/platform-tools-latest-windows.zip

2. 解压到任意目录（如 `C:\platform-tools`）

3. 添加到系统 PATH：
   - 右键"此电脑" → 属性 → 高级系统设置
   - 环境变量 → 系统变量 → Path → 编辑
   - 新建 → 输入 ADB 路径（如 `C:\platform-tools`）
   - 确定

4. 验证安装：
   ```bash
   adb version
   ```

### 设备准备

1. 开启手机开发者选项
2. 启用 USB 调试
3. 连接手机到电脑
4. 验证连接：
   ```bash
   adb devices
   ```

## 启动平台

### 使用打包的 exe（方案一完成后）

```bash
# 方式一：双击启动
start.bat

# 方式二：直接运行
MobileTestPlatform.exe
```

### 使用源码运行（方案二）

```bash
# 1. 启动 Appium（新终端）
appium

# 2. 启动平台（新终端）
run.bat
```

### 访问 Web 界面

浏览器打开：http://localhost:5000

## 快速测试

1. 打开 Web 界面
2. 点击"刷新设备列表"
3. 选择你的设备
4. 点击"连接设备"
5. 尝试各项功能：
   - 5G 网络测试
   - 灌包测试
   - 网络监控

## 文件说明

### 打包相关
- `build_with_py311.bat` - 使用 Python 3.11 打包
- `build.bat` - 完整打包脚本
- `quick_build.bat` - 快速打包
- `build.spec` - PyInstaller 配置

### 运行相关
- `run.bat` - 直接运行平台（无需打包）
- `start.bat` - 启动打包后的 exe
- `app.py` - 主程序

### 文档
- `README.md` - 项目说明
- `USAGE.md` - 使用指南
- `5G_TESTING_GUIDE.md` - 5G 测试详细指南
- `BUILD_GUIDE.md` - 打包部署指南
- `INSTALL_PYTHON311.md` - Python 3.11 安装指南
- `DEPLOYMENT_GUIDE.md` - 本文档

## 常见问题

### Q1: 找不到设备
```bash
# 检查 ADB 连接
adb devices

# 如果显示 unauthorized，在手机上允许 USB 调试
# 如果没有设备，检查 USB 连接和驱动
```

### Q2: Appium 连接失败
```bash
# 检查 Appium 是否运行
# 默认端口：4723

# 重启 Appium
# Ctrl+C 停止，然后重新运行 appium
```

### Q3: 打包失败
- 确保使用 Python 3.11 或 3.12
- 检查所有依赖是否安装
- 查看错误日志

### Q4: 网络切换不生效
- 某些功能需要 root 权限
- 检查设备是否支持 5G
- 确认 SIM 卡已开通 5G 服务

## 下一步

1. **如果要打包**：
   - 下载并安装 Python 3.11
   - 运行 `build_with_py311.bat`
   - 在 `dist` 目录找到 exe 文件

2. **如果直接使用**：
   - 确保 Appium 和 ADB 已安装
   - 运行 `run.bat`
   - 访问 http://localhost:5000

3. **查看文档**：
   - 阅读 `5G_TESTING_GUIDE.md` 了解测试功能
   - 查看 `example.py` 学习 API 调用

## 技术支持

如遇问题，请检查：
1. Python 版本是否正确
2. Appium 是否正常运行
3. ADB 是否能识别设备
4. 防火墙是否阻止连接

## 总结

- ✅ 平台功能完整，可以直接使用
- ⚠️ 打包需要 Python 3.11/3.12
- 📦 两种使用方式：打包 exe 或直接运行源码
- 📚 完整文档已提供
