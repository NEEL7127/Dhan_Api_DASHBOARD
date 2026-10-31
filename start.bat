@echo off
cd /d "%~dp0"

where python >nul 2>nul || (
    echo [ERROR] Python not found. Install Python 3.12 from python.org
    echo and tick "Add python.exe to PATH" during install, then run this again.
    pause & exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup - creating environment and installing packages...
    python -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)

echo Starting NIFTY tracker... (a browser tab will open)
.venv\Scripts\python -m streamlit run app.py
pause

