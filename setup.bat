@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set "SETUP_EXIT=%ERRORLEVEL%"
echo.
if not "%SETUP_EXIT%"=="0" (
    echo Setup did not complete successfully. Review the message above.
) else (
    echo You may close this window or press any key to continue.
)
pause >nul
exit /b %SETUP_EXIT%
