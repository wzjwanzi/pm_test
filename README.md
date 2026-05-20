# PM Test Mobile Automation Platform

桌面版基站与手机自动化测试平台，用于构建测试用例、执行抓包、基站 SSH 日志采集、灌包服务器 iperf/ping、手机侧 ADB 操作，并集中查看运行日志和产物。

## 当前架构

```text
desktop_app.py
  -> desktop.main.DesktopApp
  -> desktop.controller.DesktopController
  -> pm_tests.core.facade.PmTestRunManager
  -> pm_tests.core.planner.build_run_plan
  -> pm_tests.core.orchestrator.RunOrchestrator
  -> pm_tests.core.runner.StepRunner
  -> pm_tests.core.adapters.*
```

执行链路不依赖 Appium。手机侧操作通过 `adb` 和 Android 系统自带的 `uiautomator dump` 完成。

## 主要功能

- 用例库：保存、复制、重命名、删除用例。
- 模板导入：优先从 `cases/*.json` 读取已保存用例作为模板；空库时使用内置模板。
- 运行配置：基站 Web、基站 SSH、灌包服务器、手机侧参数分组保存到 `settings.json`。
- 执行编排：按用例步骤顺序执行，并生成 `run.json`、`execution.log`、pcap、SSH log、iperf log。
- 设备操作：通过 ADB 执行 ping、iperf、飞行模式开关、UI dump 等手机侧操作。

## 环境要求

- Windows 10/11
- Python 3.11 或 3.12
- ADB 可用，或使用项目内置 `adb.exe`
- 手机开启开发者选项和 USB 调试
- 基站 Web、基站 SSH、灌包服务器网络可达

不需要安装或启动 Appium。

## 快速启动

### 使用打包版

```bat
start.bat
```

或直接运行：

```text
release\MobileTestPlatform\MobileTestPlatform.exe
```

### 使用源码

```bat
python -m pip install -r requirements.txt
python desktop_app.py
```

## 验证

```bat
python -m pytest
```

## 重要目录

- `desktop/`：Tkinter 桌面 UI 和控制器。
- `pm_tests/core/`：运行计划、编排、步骤执行、适配器接口。
- `pm_tests/`：基站 Web、SSH、抓包、灌包服务器相关能力。
- `network/`：手机侧 iperf、ping、飞行模式等 ADB 操作。
- `device/`：ADB 设备发现和 Android UI dump 解析。
- `cases/`：本地用例库。
- `artifacts/`：运行产物目录，已被 Git 忽略。
- `release/`、`build_release/`：打包输出目录，已被 Git 忽略。

## 调用关系图

打开 `docs/project_call_graph.html` 可以查看可拖动、可播放的调用关系动态图。
