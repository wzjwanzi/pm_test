@echo off
setlocal
cd /d "%~dp0"
title MobileTestPlatform

if exist ".\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\MobileTestPlatform\MobileTestPlatform.exe"
    goto :done
)

if exist ".\release\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\release\MobileTestPlatform\MobileTestPlatform.exe"
    goto :done
)

if exist ".\dist\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\dist\MobileTestPlatform\MobileTestPlatform.exe"
    goto :done
)

echo ERROR: executable not found.
echo Expected one of:
echo   .\MobileTestPlatform\MobileTestPlatform.exe
echo   .\release\MobileTestPlatform\MobileTestPlatform.exe
echo   .\dist\MobileTestPlatform\MobileTestPlatform.exe
echo.
echo If the app still fails after launch, check:
echo   .\MobileTestPlatform\desktop_app.log
echo   .\release\MobileTestPlatform\desktop_app.log
echo   or .\dist\MobileTestPlatform\desktop_app.log

:done
pause
