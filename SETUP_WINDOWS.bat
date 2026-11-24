@echo off
setlocal
cd /d "%~dp0"
echo [1/3] Creating Python virtual environment...
py -m venv .venv
if errorlevel 1 (
    echo Python was not found. Install Python 3.10+ from python.org, then retry.
    pause
    exit /b 1
)
echo [2/3] Installing Flask and MySQL dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Check your internet connection and retry.
    pause
    exit /b 1
)
echo [3/3] Preparing your local environment configuration...
if not exist .env copy .env.example .env >nul
echo.
echo IMPORTANT: Replace YOUR_MYSQL_PASSWORD and SECRET_KEY in .env.
echo Also run migrate_existing.sql in MySQL Workbench if you used Assignments 1-7.
echo Then double-click RUN_WINDOWS.bat.
notepad .env
pause
