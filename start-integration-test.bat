@echo off
REM OSINT E-post Etterforsker - Integration Test Startup Script (Windows)
REM This script starts both frontend and backend for integration testing

echo 🚀 Starting OSINT E-post Etterforsker Integration Test...
echo =============================================

REM Check prerequisites
echo Checking prerequisites...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed
    exit /b 1
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ NPM is not installed
    exit /b 1
)

echo ✅ Prerequisites check passed

REM Check if ports are available
echo Checking ports...
netstat -an | find "LISTENING" | find ":8000" >nul 2>&1
if %errorlevel% equ 0 (
    echo ❌ Backend port 8000 is in use. Please stop the service or change the port.
    exit /b 1
)

netstat -an | find "LISTENING" | find ":3000" >nul 2>&1
if %errorlevel% equ 0 (
    echo ❌ Frontend port 3000 is in use. Please stop the service or change the port.
    exit /b 1
)

echo ✅ Ports are available

REM Create log directory
if not exist logs mkdir logs

REM Start Backend
echo Starting Backend (FastAPI)...
cd backend

REM Check if virtual environment exists
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing backend dependencies...
pip install -r ..\requirements.txt

REM Set environment variables for development
set DATABASE_URL=sqlite:///./data/osint_cache.db
set DEBUG=true
set ENVIRONMENT=development
set CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

REM Create data directory
if not exist data mkdir data

REM Start backend server
echo 🚀 Starting Backend on port 8000...
start "Backend" cmd /c "python main.py > ..\logs\backend.log 2>&1"

cd ..

REM Wait for backend to be ready
echo Waiting for Backend to be ready...
:wait_backend
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
echo ✅ Backend is ready!

REM Start Frontend
echo Starting Frontend (Next.js)...
cd frontend

REM Install dependencies
echo Installing frontend dependencies...
call npm install

REM Set environment variables for development
set NEXT_PUBLIC_API_URL=http://localhost:8000
set NEXT_PUBLIC_ENVIRONMENT=development
set NEXT_PUBLIC_DEBUG=true

REM Start frontend server
echo 🚀 Starting Frontend on port 3000...
start "Frontend" cmd /c "npm run dev > ..\logs\frontend.log 2>&1"

cd ..

REM Wait for frontend to be ready
echo Waiting for Frontend to be ready...
:wait_frontend
timeout /t 2 /nobreak >nul
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% neq 0 goto wait_frontend
echo ✅ Frontend is ready!

echo.
echo 🎉 Integration test environment is ready!
echo =============================================
echo 📱 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📚 API Documentation: http://localhost:8000/api/docs
echo ❤️ Health Check: http://localhost:8000/health
echo.
echo 📋 Logs:
echo   Backend: logs\backend.log
echo   Frontend: logs\frontend.log
echo.
echo 🛑 To stop services: stop-integration-test.bat
echo.
echo ✨ You can now test the complete OSINT system!
echo.
echo Press any key to view real-time logs, or Ctrl+C to exit...
pause >nul

REM Show real-time logs
echo Showing real-time logs (Ctrl+C to exit):
echo =============================================
powershell -command "Get-Content logs\backend.log,logs\frontend.log -Wait"