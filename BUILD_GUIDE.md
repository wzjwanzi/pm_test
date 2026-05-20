# 打包指南

## 架构说明

当前项目是 Tkinter 桌面应用，入口是：

```text
desktop_app.py
```

PyInstaller 配置文件是：

```text
build.spec
```

打包后的程序不依赖 Appium，不需要启动 Appium Server，也不需要 4723 端口。

## 环境要求

- Windows 10/11
- Python 3.11 或 3.12
- `requirements.txt` 中的 Python 依赖
- ADB 运行依赖，项目已包含 `adb.exe` 和 `scrcpy-win64-v2.0`

## 安装依赖

```bat
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 打包

推荐使用：

```bat
python -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release
```

也可以运行已有脚本：

```bat
build_release.ps1
```

或：

```bat
build.bat
quick_build.bat
```

## 输出目录

默认输出为：

```text
release\MobileTestPlatform\
```

主要文件：

- `MobileTestPlatform.exe`
- `_internal\`
- `settings.json`，首次运行或保存配置后生成。
- `cases\`，保存用例库。
- `artifacts\`，保存运行产物。

## 运行打包版

```bat
release\MobileTestPlatform\MobileTestPlatform.exe
```

或：

```bat
start.bat
```

## 分发建议

分发时保留以下结构：

```text
MobileTestPlatform/
  MobileTestPlatform.exe
  _internal/
  cases/
  settings.json
```

`settings.json` 和 `cases/` 是运行数据，可以按现场环境保留或替换。`artifacts/` 是运行产物目录，通常不需要随安装包分发。

## 验证

打包前：

```bat
python -m pytest
python -m py_compile config.py app_settings.py desktop_app.py desktop\controller.py pm_tests\core\facade.py
```

打包后：

```bat
release\MobileTestPlatform\MobileTestPlatform.exe
```

如果启动失败，查看：

```text
release\MobileTestPlatform\desktop_app.log
```

## 常见问题

### Tkinter 启动失败

确认 `build.spec` 中包含 `_tkinter.pyd`、`tcl86t.dll`、`tk86t.dll`、`_tcl_data` 和 `_tk_data`。

### ADB 不可用

确认项目内置 `adb.exe` 存在，或系统 PATH 中有 Android Platform Tools。

### GitHub 上传失败

检查网络是否能连接 `github.com:443`。这与项目打包无关。
