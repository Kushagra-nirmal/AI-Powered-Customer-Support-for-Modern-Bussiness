@echo off
echo ========================================================
echo Launching SupportAI ^& J.A.R.V.I.S. in Default Browser...
echo ========================================================
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue) { Start-Process 'http://127.0.0.1:8001/' } else { Start-Process 'http://127.0.0.1:8000/' }"
exit
