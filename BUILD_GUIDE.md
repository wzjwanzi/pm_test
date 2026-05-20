# 打包部署指南

## 概述

本指南介绍如何将移动设备自动化测试平台打包成独立的可执行文件（exe），使其能在任意 Windows 环境下运行，无需安装 Python 环境。

## 打包前准备

### 1. 系统要求

- Windows 10/11 或 Linux/macOS
- Python 3.8 或更高版本
- 至少 2GB 可用磁盘空间

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

这将安装所有必需的依赖，包括 PyInstaller。

## Windows 打包

### 方法一：使用自动打包脚本（推荐）

1. 双击运行 `build.bat`
2. 等待打包完成（约 3-5 分钟）
3. 打包完成后，可执行文件位于 `release\MobileTestPlatform.exe`

### 方法二：手动打包

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 清理旧文件
rmdir /s /q build dist

# 3. 执行打包
pyinstaller build.spec --clean

# 4. 复制文件到发布目录
mkdir release
copy dist\MobileTestPlatform.exe release\
copy README.md release\
copy USAGE.md release\
copy 5G_TESTING_GUIDE.md release\
```

## Linux/macOS 打包

### 使用打包脚本

```bash
# 1. 添加执行权限
chmod +x build.sh

# 2. 运行打包脚本
./build.sh

# 3. 可执行文件位于 release/MobileTestPlatform
```

## 打包配置说明

### build.spec 文件

这是 PyInstaller 的配置文件，包含以下关键配置：

- **入口文件**: `app.py`
- **包含的数据文件**:
  - `templates/` - Web 界面模板
  - `config.py` - 配置文件
- **隐藏导入**: 所有必需的 Python 模块
- **输出文件名**: `MobileTestPlatform.exe`

### 自定义配置

如需修改打包配置，编辑 `build.spec` 文件：

```python
# 修改应用名称
name='YourAppName',

# 添加图标（需要 .ico 文件）
icon='icon.ico',

# 修改为窗口模式（无控制台）
console=False,
```

## 使用打包后的程序

### Windows

1. 将 `release` 文件夹复制到目标机器
2. 双击 `start.bat` 启动服务
3. 或直接运行 `MobileTestPlatform.exe`
4. 浏览器访问 `http://localhost:5000`

### Linux/macOS

```bash
cd release
./MobileTestPlatform
```

## 依赖环境

打包后的程序仍需要以下外部工具：

### 必需组件

1. **Appium Server**
   ```bash
   npm install -g appium
   appium driver install uiautomator2
   ```

2. **ADB (Android Debug Bridge)**
   - 下载 Android SDK Platform Tools
   - 添加到系统 PATH

### 启动顺序

```bash
# 1. 启动 Appium 服务
appium

# 2. 启动测试平台（新终端）
MobileTestPlatform.exe
```

## 分发部署

### 创建完整安装包

建议将以下文件打包在一起分发：

```
MobileTestPlatform/
├── MobileTestPlatform.exe    # 主程序
├── start.bat                  # 启动脚本
├── README.md                  # 说明文档
├── USAGE.md                   # 使用指南
├── 5G_TESTING_GUIDE.md       # 5G测试指南
└── tools/                     # 可选：包含 Appium 和 ADB
    ├── appium/
    └── platform-tools/
```

### 制作安装程序（可选）

使用 Inno Setup 或 NSIS 创建安装程序：

1. 下载 Inno Setup
2. 创建安装脚本
3. 包含所有必需文件
4. 生成 setup.exe

## 常见问题

### 1. 打包失败

**问题**: PyInstaller 报错找不到模块

**解决**:
```bash
# 清理缓存重新打包
pyinstaller --clean build.spec
```

### 2. 运行时缺少 DLL

**问题**: 提示缺少 VCRUNTIME140.dll

**解决**: 安装 Visual C++ Redistributable
- 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe

### 3. 模板文件找不到

**问题**: Flask 提示找不到 templates 目录

**解决**: 确保 build.spec 中包含了 templates 目录
```python
datas=[
    ('templates', 'templates'),
],
```

### 4. 程序体积过大

**问题**: exe 文件超过 100MB

**解决**:
- 使用 UPX 压缩（已在 spec 中启用）
- 排除不必要的模块
- 考虑使用 onedir 模式而非 onefile

### 5. 防火墙拦截

**问题**: Windows 防火墙阻止程序运行

**解决**:
- 添加防火墙例外
- 或使用管理员权限运行

## 优化建议

### 减小文件体积

1. **排除不必要的模块**
   ```python
   excludes=[
       'matplotlib',
       'numpy',
       'pandas',
   ],
   ```

2. **使用虚拟环境**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   pyinstaller build.spec
   ```

### 提升启动速度

1. 使用 onedir 模式（文件夹形式）
2. 禁用 UPX 压缩
3. 减少隐藏导入

## 持续集成

### GitHub Actions 自动打包

创建 `.github/workflows/build.yml`:

```yaml
name: Build Executable

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pyinstaller build.spec --clean
      - uses: actions/upload-artifact@v2
        with:
          name: MobileTestPlatform
          path: dist/MobileTestPlatform.exe
```

## 版本管理

建议在 `config.py` 中添加版本信息：

```python
VERSION = "1.0.0"
BUILD_DATE = "2024-04-25"
```

在程序启动时显示版本信息。

## 技术支持

如遇到打包问题，请检查：

1. Python 版本是否兼容
2. 所有依赖是否正确安装
3. PyInstaller 版本是否最新
4. 查看打包日志文件

## 更新日志

### v1.0.0 (2024-04-25)
- 初始版本
- 支持 Windows/Linux/macOS 打包
- 包含完整的 5G 测试和灌包测试功能
