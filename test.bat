@echo off
cd /d "%~dp0"
echo ==========================================================
echo  Running Live API End-to-End Tests
echo ==========================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0scripts\test_live_api.ps1"
pause
