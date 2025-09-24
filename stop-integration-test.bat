@echo off
REM OSINT E-post Etterforsker - Integration Test Stop Script (Windows)
REM This script stops both frontend and backend services

echo 🛑 Stopping OSINT E-post Etterforsker Integration Test...
echo =============================================

REM Stop processes by window title (from start command)
echo Stopping Backend...
taskkill /fi "WindowTitle eq Backend*" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend stopped successfully
) else (
    echo ⚠️ Backend was not running or already stopped
)

echo Stopping Frontend...
taskkill /fi "WindowTitle eq Frontend*" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Frontend stopped successfully
) else (
    echo ⚠️ Frontend was not running or already stopped
)

REM Stop processes by port as backup
echo Checking for services by port...

REM Stop Backend (port 8000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo Stopping process on port 8000 (PID: %%a)...
    taskkill /pid %%a /f >nul 2>&1
)

REM Stop Frontend (port 3000)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do (
    echo Stopping process on port 3000 (PID: %%a)...
    taskkill /pid %%a /f >nul 2>&1
)

REM Stop any Python processes running main.py (backend)
echo Cleaning up any remaining backend processes...
taskkill /im python.exe /f >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Stopped Python backend processes
) else (
    echo ⚠️ No Python backend processes found
)

REM Stop any Node.js processes (frontend)
echo Cleaning up any remaining frontend processes...
taskkill /im node.exe /f >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Stopped Node.js frontend processes
) else (
    echo ⚠️ No Node.js frontend processes found
)

REM Show log files info
echo Log files:
if exist logs\backend.log (
    for %%i in (logs\backend.log) do echo   Backend log: logs\backend.log (%%~zi bytes)
)
if exist logs\frontend.log (
    for %%i in (logs\frontend.log) do echo   Frontend log: logs\frontend.log (%%~zi bytes)
)

REM Verify ports are free
echo Verifying ports are free...
timeout /t 2 /nobreak >nul

netstat -an | find "LISTENING" | find ":8000" >nul 2>&1
if %errorlevel% neq 0 (
    echo ✅ Port 8000 (Backend) is free
) else (
    echo ❌ Port 8000 (Backend) is still in use
)

netstat -an | find "LISTENING" | find ":3000" >nul 2>&1
if %errorlevel% neq 0 (
    echo ✅ Port 3000 (Frontend) is free
) else (
    echo ❌ Port 3000 (Frontend) is still in use
)

echo.
echo 🎉 Integration test environment stopped!
echo =============================================
echo 📋 Summary:
echo   • Backend (FastAPI) stopped
echo   • Frontend (Next.js) stopped
echo   • Ports 8000 and 3000 released
echo.
echo 💡 Tips:
echo   • Log files are preserved in logs\ directory
echo   • To restart: start-integration-test.bat
echo   • To clean logs: del logs\*.log
echo.
echo ✨ Ready for next integration test!

pause