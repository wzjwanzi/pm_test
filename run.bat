@echo off
setlocal
cd /d "%~dp0"
title MobileTestPlatform

if exist ".\release\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\release\MobileTestPlatform\MobileTestPlatform.exe"
    goto :eof
)

if exist ".\dist\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\dist\MobileTestPlatform\MobileTestPlatform.exe"
    goto :eof
)

if exist ".\MobileTestPlatform\MobileTestPlatform.exe" (
    start "" ".\MobileTestPlatform\MobileTestPlatform.exe"
    goto :eof
)

echo ERROR: executable not found.
echo Expected one of:
echo   .\release\MobileTestPlatform\MobileTestPlatform.exe
echo   .\dist\MobileTestPlatform\MobileTestPlatform.exe
echo   .\MobileTestPlatform\MobileTestPlatform.exe
pause
