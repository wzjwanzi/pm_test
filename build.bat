@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo Mobile Test Platform Build
echo ========================================
echo.

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.8+ not found.
    pause
    exit /b 1
)
echo Python OK
echo.

echo [2/5] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements.
    pause
    exit /b 1
)
echo Requirements OK
echo.

echo [3/5] Cleaning old build output...
if exist build_release rmdir /s /q build_release
if exist release\MobileTestPlatform rmdir /s /q release\MobileTestPlatform
if exist release\MobileTestPlatform.exe del /f /q release\MobileTestPlatform.exe
if exist __pycache__ rmdir /s /q __pycache__
echo Clean complete
echo.

echo [4/5] Building package...
pyinstaller build.spec --clean --noconfirm --distpath release --workpath build_release
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)
echo Build complete
echo.

echo [5/5] Copying runtime config and docs...
if not exist release mkdir release
if exist settings.json copy /Y settings.json release\MobileTestPlatform\settings.json >nul
if exist cases xcopy /E /I /Y cases release\MobileTestPlatform\cases >nul
copy /Y README.md release\ >nul
copy /Y USAGE.md release\ >nul
copy /Y 5G_TESTING_GUIDE.md release\ >nul
copy /Y start.bat release\start.bat >nul
copy /Y run.bat release\run.bat >nul
echo Release prepared
echo.

echo ========================================
echo Build succeeded
echo EXE: release\MobileTestPlatform\MobileTestPlatform.exe
echo ========================================
echo.
pause
