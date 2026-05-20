# Python 3.11 安装指南

## 为什么需要安装 Python 3.11？

你当前使用的是 Python 3.14.0a1（alpha 开发版），PyInstaller 还不支持此版本。
需要安装稳定版 Python 3.11 来进行打包。

## 安装步骤

### 1. 下载 Python 3.11

访问官网下载页面：
https://www.python.org/downloads/release/python-31110/

或直接下载链接（Windows 64位）：
https://www.python.org/ftp/python/3.11.10/python-3.11.10-amd64.exe

### 2. 安装 Python 3.11

运行下载的安装程序，**重要设置**：

1. ✅ **勾选** "Add Python 3.11 to PATH"
2. ✅ **勾选** "Install for all users"（可选）
3. 点击 "Customize installation"
4. 确保勾选：
   - pip
   - py launcher
   - for all users (recommended)
5. 点击 "Install"

### 3. 验证安装

安装完成后，打开新的命令行窗口：

```bash
# 查看所有已安装的 Python 版本
py --list

# 应该看到类似输出：
# -3.14-64  *
# -3.11-64

# 测试 Python 3.11
py -3.11 --version
# 输出: Python 3.11.10
```

### 4. 使用 Python 3.11 打包

安装完成后，运行打包脚本：

```bash
# 方式一：使用专用脚本（推荐）
build_with_py311.bat

# 方式二：手动命令
py -3.11 -m pip install -r requirements.txt
py -3.11 -m PyInstaller build.spec --clean
```

## 常见问题

### Q1: 安装后 py --list 看不到 3.11？
A: 重新打开命令行窗口，或重启电脑

### Q2: 提示 "py" 不是内部或外部命令？
A: 重新安装 Python，确保勾选 "Add Python to PATH"

### Q3: 两个 Python 版本会冲突吗？
A: 不会。使用 `py -3.11` 指定版本即可

### Q4: 可以卸载 Python 3.14 吗？
A: 可以，但建议保留。使用 py launcher 可以同时管理多个版本

## 快速安装（使用 winget）

如果你的系统有 winget（Windows 11 自带）：

```bash
winget install Python.Python.3.11
```

## 快速安装（使用 Chocolatey）

如果你安装了 Chocolatey：

```bash
choco install python311
```

## 安装后的下一步

1. 验证安装：`py -3.11 --version`
2. 运行打包脚本：`build_with_py311.bat`
3. 等待打包完成
4. 在 `dist` 或 `release` 目录找到 `MobileTestPlatform.exe`

## 需要帮助？

如果遇到问题，请检查：
- 是否使用管理员权限运行安装程序
- 是否勾选了 "Add to PATH"
- 是否重新打开了命令行窗口
