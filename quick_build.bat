@echo off
chcp 65001 >nul
setlocal

echo Quick build...
echo.

if exist build_release rmdir /s /q build_release
if exist release\MobileTestPlatform rmdir /s /q release\MobileTestPlatform
if exist release\MobileTestPlatform.exe del /f /q release\MobileTestPlatform.exe

pyinstaller build.spec --clean --noconfirm --distpath release --workpath build_release

if %errorlevel% equ 0 (
    if not exist release mkdir release
    if exist settings.json copy /Y settings.json release\MobileTestPlatform\settings.json >nul
    copy /Y README.md release\ >nul
    copy /Y USAGE.md release\ >nul
    copy /Y 5G_TESTING_GUIDE.md release\ >nul
    copy /Y start.bat release\start.bat >nul
    copy /Y run.bat release\run.bat >nul
)

if %errorlevel% equ 0 (
    echo.
    echo Build succeeded
    echo EXE: release\MobileTestPlatform\MobileTestPlatform.exe
    echo.
) else (
    echo.
    echo Build failed
    echo.
    pause
    exit /b 1
)
