@echo off
cd /d "%~dp0"
echo ==========================================================
echo  Starting SupportAI Customer Support
echo ==========================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0deploy_production.ps1"
if errorlevel 1 (
    echo.
    echo Fallback: starting directly via Python...
    ".venv\Scripts\python.exe" run.py
)
pause
