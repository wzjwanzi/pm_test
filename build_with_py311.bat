@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo Build with Python 3.11
echo ========================================
echo.

echo [1/4] Checking Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 not found.
    pause
    exit /b 1
)
py -3.11 --version
echo Python 3.11 OK
echo.

echo [2/4] Installing requirements...
py -3.11 -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)
echo Requirements OK
echo.

echo [3/4] Cleaning old output...
if exist build_release rmdir /s /q build_release
if exist release\MobileTestPlatform rmdir /s /q release\MobileTestPlatform
if exist release\MobileTestPlatform.exe del /f /q release\MobileTestPlatform.exe
echo Clean complete
echo.

echo [4/4] Building package...
py -3.11 -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)
echo Build complete
echo.

if not exist release mkdir release
copy /Y README.md release\ >nul
copy /Y USAGE.md release\ >nul
copy /Y 5G_TESTING_GUIDE.md release\ >nul
copy /Y start.bat release\start.bat >nul
copy /Y run.bat release\run.bat >nul

echo ========================================
echo Build succeeded
echo EXE: release\MobileTestPlatform\MobileTestPlatform.exe
echo ========================================
echo.
pause
