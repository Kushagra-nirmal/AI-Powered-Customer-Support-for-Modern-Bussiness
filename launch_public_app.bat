@echo off
title SupportAI & JARVIS - Global Public Deployment
echo Starting SupportAI & JARVIS Global Public Deployment...
powershell -ExecutionPolicy Bypass -File "%~dp0deploy_public_url.ps1" -OpenBrowser
pause
