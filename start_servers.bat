@echo off
title Riko Project Server Launcher
echo ======================================
echo    Starting Riko Project Servers...
echo ======================================
echo.

:: ----------------------------
:: User Configuration
:: ----------------------------
:: Path to your GPT-SoVITS root folder
set SOVITS_PATH=D:\PyProjects\GPT-SoVITS-v3lora-20250228\GPT-SoVITS-v3lora-20250228 

:: ----------------------------
:: Auto paths (relative to this .bat file)
:: ----------------------------
set PROJECT_ROOT=%~dp0
set VENV_PATH=%PROJECT_ROOT%.venv
set SERVER_PATH=%PROJECT_ROOT%server
set CLIENT_PATH=%PROJECT_ROOT%client

:: ----------------------------
:: Start animation server
:: ----------------------------
echo Starting animation server...
start "Animation Server" cmd /k "cd /d %SERVER_PATH% && call %VENV_PATH%\Scripts\activate && python server.py"

:: ----------------------------
:: Start Vite client
:: ----------------------------
echo Starting Vite client...
start "Vite Client" cmd /k "cd /d %CLIENT_PATH% && npx vite"

:: ----------------------------
:: Start GPT-SoVITS server
:: ----------------------------
echo Starting GPT-SoVITS Server (using run_api_v2.bat)...
start "GPT-SoVITS" cmd /k "cd /d %SOVITS_PATH% && call go-api.bat"

echo.
echo ✅ All servers are launching in separate windows!
pause
