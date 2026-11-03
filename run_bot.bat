@echo off
REM Queue Bot Runner for Windows

echo.
echo ========================================
echo   Queue Bot - 24/7 Monitor
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

echo Checking dependencies...
pip show aiogram >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -q -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting bot in live mode...
echo MODE=live will be used. Edit .env to change.
echo.
echo Press Ctrl+C to stop the bot.
echo.

REM Run the bot with proper error handling
python bot.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Bot crashed with exit code %errorlevel%
    echo Check the log above for details.
    pause
)
