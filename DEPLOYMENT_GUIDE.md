# 部署指南

## 当前部署方式

项目当前以 Windows 桌面程序部署，入口为：

```text
MobileTestPlatform.exe
```

运行链路不使用 Appium。手机侧能力通过 ADB 命令和 Android 自带 `uiautomator dump` 实现。

## 目标机器要求

- Windows 10/11
- 可连接手机的 USB 驱动环境
- ADB 可用，或使用安装包内置 ADB
- 能访问基站 Web
- 能 SSH 到基站
- 能 SSH 到灌包服务器

不需要 Node.js、Appium、UiAutomator2 driver 或 Appium Inspector。

## 部署目录

推荐目录结构：

```text
MobileTestPlatform/
  MobileTestPlatform.exe
  _internal/
  cases/
  settings.json
  artifacts/
```

说明：

- `_internal/`：PyInstaller 依赖目录，必须保留。
- `cases/`：用例库。
- `settings.json`：现场运行配置。
- `artifacts/`：运行产物，可按需清理。

## 首次配置

1. 启动 `MobileTestPlatform.exe`。
2. 打开运行配置。
3. 配置并保存：
   - 基站 Web
   - 基站 SSH
   - 灌包服务器
   - 手机侧参数
   - 通用参数
4. 在用例库中确认模板和保存用例是否存在。
5. 连接手机后点击刷新设备。

## 执行前检查

### 手机

```bat
adb devices
adb shell getprop ro.product.model
adb shell uiautomator dump
```

### 基站 SSH

手动确认能登录，并验证日志命令、RRC release 命令、force-rlc-escape 命令能执行。

### 灌包服务器

手动确认能登录，并验证 iperf/ping 命令能执行。

示例：

```bash
iperf -u -c <phone_ip> -i 1 -t 60 -b 250m -l 1350 -p 6011 -P 1
iperf -u -s -i 1 -p 7011
```

## 日志与产物

运行结果默认在：

```text
artifacts\test_runs\<run_id>\
```

重点文件：

- `run.json`：结构化结果。
- `execution.log`：步骤、命令、输出、错误和产物记录。
- 用例目录：`用例名字_日期_时间`。
- pcap、SSH log、iperf log、ping log。

## 常见问题

### 找不到手机

执行：

```bat
adb devices
```

如果没有设备，检查 USB 线、驱动、USB 调试授权。

### UI dump 失败

执行：

```bat
adb shell uiautomator dump
```

如果失败，检查手机是否解锁、是否允许调试、当前页面是否可访问。

### 抓包没有生成

检查：

- Web 抓包开始步骤是否执行。
- 抓包是否早于手机入网或灌包步骤。
- Web 抓包停止步骤是否执行。
- `execution.log` 中 Web 抓包步骤是否报错。

### SSH 日志没有生成

检查：

- start/stop 步骤是否成对存在。
- SSH 命令是否能手动执行。
- 日志输出目录是否可写。
- `execution.log` 中是否能看到命令输入输出。

### 灌包太快结束

通过用例步骤里的“通用延时”控制持续时间。每个延时步骤都可以单独配置秒数。

## 维护建议

- 不要把 `artifacts/`、`release/`、`build_release/` 提交到 Git。
- 现场配置保存在 `settings.json`，包含密码时不要上传到公共仓库。
- 用例库保存在 `cases/`，需要复用模板时可复制对应 JSON。
