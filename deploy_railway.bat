@echo off
title SupportAI Railway Cloud Deployment
cls
echo ====================================================================
echo   SupportAI ^& JARVIS — 24/7 Autonomous Cloud Deployment on Railway
echo   Author: Nirmal Sharma
echo ====================================================================
echo.
echo Railway provides 24/7 uptime with a PERMANENT fixed domain.
echo No PC required, no sleep timeouts, and ZERO Error 1016 issues!
echo.
echo Select an action:
echo   [1] Log in to Railway (Opens your browser to authenticate)
echo   [2] Deploy directly to Railway (railway init + railway up)
echo   [3] Open Railway Dashboard (Manage services, add Postgres database)
echo   [4] Check Railway Account Status
echo   [5] Push to GitHub (for automatic GitHub-to-Railway sync)
echo.
set /p opt="Enter your choice (1-5): "

if "%opt%"=="1" (
    echo.
    echo Logging in to Railway...
    cmd /c railway login
    goto end
)

if "%opt%"=="2" (
    echo.
    echo Initializing and deploying to Railway...
    echo Step 1: Linking/Creating project...
    cmd /c railway init
    echo.
    echo Step 2: Uploading code and starting build...
    cmd /c railway up
    echo.
    echo Step 3: Generating permanent public domain...
    cmd /c railway domain
    goto end
)

if "%opt%"=="3" (
    echo.
    echo Opening Railway Dashboard in your browser...
    cmd /c railway open
    goto end
)

if "%opt%"=="4" (
    echo.
    cmd /c railway whoami
    goto end
)

if "%opt%"=="5" (
    echo.
    set /p repourl="Enter your GitHub Repository URL (e.g. https://github.com/username/supportai.git): "
    if not "%repourl%"=="" (
        git remote remove origin 2>nul
        git remote add origin %repourl%
        git branch -M main
        git push -u origin main
        echo.
        echo Code successfully pushed to GitHub!
        echo Now go to https://railway.app, click 'New Project' -^> 'Deploy from GitHub repo'.
    )
    goto end
)

:end
echo.
echo ====================================================================
pause
