# 打包说明 - Python 版本兼容性

## 当前问题

你的系统使用 Python 3.14.0a1（alpha 版本），PyInstaller 目前还不完全支持此版本。

## 解决方案

### 方案一：使用稳定版 Python 打包（推荐）

1. 安装 Python 3.11 或 3.12（稳定版本）
   - 下载地址：https://www.python.org/downloads/
   - 推荐版本：Python 3.11.x 或 3.12.x

2. 使用稳定版 Python 执行打包
   ```bash
   # 使用 py launcher 指定版本
   py -3.11 -m pip install -r requirements.txt
   py -3.11 -m PyInstaller build.spec --clean
   ```

### 方案二：直接分发 Python 脚本

如果不方便安装其他 Python 版本，可以直接分发源码：

1. 创建启动脚本 `run.bat`：
   ```batch
   @echo off
   echo 正在启动移动设备自动化测试平台...
   python app.py
   pause
   ```

2. 用户需要：
   - 安装 Python 3.8+
   - 运行 `pip install -r requirements.txt`
   - 双击 `run.bat` 启动

### 方案三：使用 Docker 容器化

创建 Docker 镜像，完全隔离环境：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]
```

## 临时解决方案

在修复 Python 版本问题之前，你可以：

1. 直接运行源码：
   ```bash
   python app.py
   ```

2. 或创建虚拟环境使用稳定版本：
   ```bash
   # 如果系统有多个 Python 版本
   py -3.11 -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   pyinstaller build.spec --clean
   ```

## 推荐做法

为了确保最佳兼容性，建议：
- 使用 Python 3.11.x 或 3.12.x 进行打包
- Python 3.14 仍在开发中，不建议用于生产环境
- 打包后的 exe 可以在任何 Windows 系统运行，无需 Python

## 检查系统 Python 版本

```bash
# 查看所有已安装的 Python 版本
py --list

# 使用特定版本
py -3.11 --version
py -3.12 --version
```
