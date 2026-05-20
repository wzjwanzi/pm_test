@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
set "SDK_DIR=%PROJECT_DIR%scrcpy-win64-v2.0"
set "APPIUM_CMD=%APPDATA%\npm\appium.cmd"

if not exist "%APPIUM_CMD%" (
    echo 未找到 Appium 启动命令: %APPIUM_CMD%
    echo 请先执行: npm install -g appium
    exit /b 1
)

if not exist "%SDK_DIR%\adb.exe" (
    echo 未找到 adb.exe: %SDK_DIR%\adb.exe
    exit /b 1
)

set "ANDROID_HOME=%SDK_DIR%"
set "ANDROID_SDK_ROOT=%SDK_DIR%"

echo ANDROID_HOME=%ANDROID_HOME%
echo Appium 启动中: http://127.0.0.1:4723/wd/hub
echo 按 Ctrl+C 可停止服务
echo.

call "%APPIUM_CMD%" --base-path /wd/hub --port 4723
