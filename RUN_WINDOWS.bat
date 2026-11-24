@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Python dependencies are not installed. Run SETUP_WINDOWS.bat first.
    pause
    exit /b 1
)
if not exist .env (
    echo Missing .env. Run SETUP_WINDOWS.bat first.
    pause
    exit /b 1
)
echo Checking MySQL database...
".venv\Scripts\python.exe" check_database.py
if errorlevel 1 (
    echo Fix the MySQL setup above before running the website.
    pause
    exit /b 1
)
echo.
echo Starting ApplyFlow. Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C in this window to stop the server.
".venv\Scripts\python.exe" app.py
pause
