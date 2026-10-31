@echo off
cd /d "%~dp0"
title Dhan Live Option Chain to Excel
echo Starting Dhan Live Option Chain Stream to Excel...
.venv\Scripts\python.exe dhan_oc.py
pause

