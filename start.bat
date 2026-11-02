@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Dhan Option Chain Dashboard & Live Excel Tracker

echo ============================================================
echo   DHAN OPTION CHAIN DASHBOARD & LIVE EXCEL STREAMER
echo ============================================================
echo.

:: 1. Detect Python
set "PYTHON_EXE="
where python >nul 2>nul && (
    python --version >nul 2>nul && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
    where py >nul 2>nul && (
        py -3 --version >nul 2>nul && set "PYTHON_EXE=py -3"
    )
)
if not defined PYTHON_EXE (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
    )
)
if not defined PYTHON_EXE (
    for /d %%D in ("C:\Python3*") do (
        if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] Python is not installed or not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to tick "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Check / Create Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] First-time setup detected.
    echo [INFO] Creating virtual environment (.venv)...
    %PYTHON_EXE% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing required libraries...
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Package installation failed.
        pause
        exit /b 1
    )
    echo [INFO] Environment successfully created!
    echo.
) else (
    :: Quick verification that required packages exist
    .venv\Scripts\python.exe -c "import streamlit, xlwings, pandas, openpyxl, requests" >nul 2>nul
    if errorlevel 1 (
        echo [INFO] Updating packages from requirements.txt...
        .venv\Scripts\python.exe -m pip install -r requirements.txt
    )
)

:: 3. Launch Menu / Auto-start
echo Choose an option (auto-starting Web Dashboard in 3 seconds):
echo   [1] Start Web Dashboard (Streamlit + Live Excel Streaming)
echo   [2] Start Standalone Console Streamer (OptionChain.xlsx)
echo.

choice /c 12 /n /t 3 /d 1 /m "Select [1] or [2] (Default is 1): "
if errorlevel 2 goto run_console
goto run_dashboard

:run_dashboard
echo.
echo [INFO] Starting Dhan Web Dashboard at http://localhost:8501 ...
echo [INFO] A browser tab will open automatically.
echo [INFO] Press Ctrl+C in this window to stop.
echo.
.venv\Scripts\python.exe -m streamlit run app.py
goto end

:run_console
echo.
echo [INFO] Starting Live Option Chain Console Streamer -> OptionChain.xlsx ...
echo [INFO] Press Ctrl+C in this window to stop.
echo.
.venv\Scripts\python.exe dhan_oc.py
goto end

:end
pause
