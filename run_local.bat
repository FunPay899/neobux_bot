@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

if not exist venv (
    echo [1/3] Creating virtual environment...
    py -3.11 -m venv venv 2>nul || python -m venv venv
)

call venv\Scripts\activate.bat

if exist requirements.txt (
    echo [2/3] Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [3/3] Starting bot...
python bot.py

pause
