@echo off
echo ============================================================
echo  In-Car AI Voice Assistant — Windows Setup
echo ============================================================
echo.

:: Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv .venv

:: Activate it
call .venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install all dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Check for .env file
if not exist .env (
    echo.
    echo WARNING: .env file not found.
    echo Copying .env_example to .env — fill in your API keys before running.
    copy .env_example .env
)

echo.
echo ============================================================
echo  Setup complete!
echo  To run: .venv\Scripts\activate  then  python main.py
echo ============================================================
pause
