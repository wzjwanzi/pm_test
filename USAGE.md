# 使用指南

## 准备环境

1. 安装 Python 依赖：

   ```bat
   python -m pip install -r requirements.txt
   ```

2. 确认 ADB 可用：

   ```bat
   adb devices
   ```

   如果系统 PATH 中没有 ADB，可以使用项目根目录或 `scrcpy-win64-v2.0` 中的 `adb.exe`。

3. 准备手机：

   - 开启开发者选项。
   - 开启 USB 调试。
   - 连接电脑并在手机上允许调试授权。

4. 准备外部系统：

   - 基站 Web 地址、账号、密码。
   - 基站 SSH 地址、账号、密码和日志命令。
   - 灌包服务器 SSH 地址、账号、密码和 iperf/ping 命令。

不需要启动 Appium，也不需要 4723 端口。

## 启动平台

### 打包版

```bat
start.bat
```

或：

```bat
release\MobileTestPlatform\MobileTestPlatform.exe
```

### 源码版

```bat
python desktop_app.py
```

## 基本使用流程

1. 打开运行配置，分别配置：
   - 基站 Web
   - 基站 SSH
   - 灌包服务器
   - 手机侧参数
   - 通用参数

2. 在用例库中选择或创建用例。

3. 在步骤顺序中添加步骤，例如：
   - Web 抓包开始/停止
   - SSH RLC/UP 日志开始/停止
   - SSH 速率日志开始/停止
   - SSH CPU 日志开始/停止
   - RRC release 重复执行
   - force-rlc-escape 重复执行
   - 手机飞行操作
   - 灌包服务器下行/上行 iperf
   - 手机侧下行接收/上行发送
   - 通用延时

4. 点击步骤可编辑当前步骤参数，编辑后点击保存。

5. 选择设备，将用例加入队列，点击开始。

6. 在结果详情和实时日志中查看：
   - 所有操作日志
   - SSH 命令输入输出
   - 灌包输出
   - 抓包文件
   - `execution.log`

## 运行产物

默认写入：

```text
artifacts/test_runs/<run_id>/
```

每个用例会按以下格式创建目录：

```text
用例名字_日期_时间
```

常见文件：

- `run.json`：运行状态与结果。
- `execution.log`：步骤开始/结束、命令、错误和产物记录。
- `*.pcap`：抓包文件。
- `*.log`：SSH、iperf、ping 等日志。

## 常见问题

### 找不到设备

```bat
adb devices
```

如果显示 `unauthorized`，需要在手机上确认 USB 调试授权。如果没有设备，检查 USB 线、驱动和手机 USB 模式。

### 手机 UI 操作失败

项目使用的是：

```bat
adb shell uiautomator dump
```

这是 Android 系统自带命令，不是 Appium。失败时请检查：

- 手机是否解锁。
- 当前页面是否可交互。
- ADB 是否有权限。
- `adb shell uiautomator dump` 是否能单独执行成功。

### 没有 pcap

检查：

- Web 抓包开始步骤是否先于手机入网/灌包。
- Web 抓包停止步骤是否执行。
- 基站 Web 配置的下载目录是否可写。
- `execution.log` 中 Web 抓包开始/停止是否有错误。

### SSH 日志为空

检查：

- SSH 地址、账号、密码是否正确。
- 命令是否能在终端手动执行。
- 用例里是否包含对应的 stop 步骤。
- `execution.log` 中是否记录了命令输入输出。

## 调用关系

打开：

```text
docs/project_call_graph.html
```

可以查看项目调用关系动态图。
