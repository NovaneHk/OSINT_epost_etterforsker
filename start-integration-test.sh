#!/bin/bash

# OSINT E-post Etterforsker - Integration Test Startup Script
# This script starts both frontend and backend for integration testing

set -e

echo "🚀 Starting OSINT E-post Etterforsker Integration Test..."
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null; then
        echo -e "${YELLOW}Warning: Port $1 is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    echo -e "${BLUE}Waiting for $service_name to be ready...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s $url > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi

        echo -e "${YELLOW}Attempt $attempt/$max_attempts - $service_name not ready yet...${NC}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ $service_name failed to start after $max_attempts attempts${NC}"
    return 1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ NPM is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Check if ports are available
echo -e "${BLUE}Checking ports...${NC}"
BACKEND_PORT=8000
FRONTEND_PORT=3000

if ! check_port $BACKEND_PORT; then
    echo -e "${RED}❌ Backend port $BACKEND_PORT is in use. Please stop the service or change the port.${NC}"
    exit 1
fi

if ! check_port $FRONTEND_PORT; then
    echo -e "${RED}❌ Frontend port $FRONTEND_PORT is in use. Please stop the service or change the port.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ports are available${NC}"

# Create log directory
mkdir -p logs

# Start Backend
echo -e "${BLUE}Starting Backend (FastAPI)...${NC}"
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing backend dependencies...${NC}"
pip install -r ../requirements.txt

# Set environment variables for development
export DATABASE_URL="sqlite:///./data/osint_cache.db"
export DEBUG="true"
export ENVIRONMENT="development"
export CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

# Create data directory
mkdir -p data

# Start backend server
echo -e "${GREEN}🚀 Starting Backend on port $BACKEND_PORT...${NC}"
python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid

cd ..

# Wait for backend to be ready
if ! wait_for_service "http://localhost:$BACKEND_PORT/health" "Backend"; then
    echo -e "${RED}❌ Failed to start backend${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start Frontend
echo -e "${BLUE}Starting Frontend (Next.js)...${NC}"
cd frontend

# Install dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
npm install

# Set environment variables for development
export NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT"
export NEXT_PUBLIC_ENVIRONMENT="development"
export NEXT_PUBLIC_DEBUG="true"

# Start frontend server
echo -e "${GREEN}🚀 Starting Frontend on port $FRONTEND_PORT...${NC}"
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../logs/frontend.pid

cd ..

# Wait for frontend to be ready
if ! wait_for_service "http://localhost:$FRONTEND_PORT" "Frontend"; then
    echo -e "${RED}❌ Failed to start frontend${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Integration test environment is ready!${NC}"
echo "============================================="
echo -e "${BLUE}📱 Frontend:${NC} http://localhost:$FRONTEND_PORT"
echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:$BACKEND_PORT"
echo -e "${BLUE}📚 API Documentation:${NC} http://localhost:$BACKEND_PORT/api/docs"
echo -e "${BLUE}❤️ Health Check:${NC} http://localhost:$BACKEND_PORT/health"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo -e "  Backend: logs/backend.log"
echo -e "  Frontend: logs/frontend.log"
echo ""
echo -e "${YELLOW}🛑 To stop services:${NC}"
echo -e "  ./stop-integration-test.sh"
echo ""
echo -e "${GREEN}✨ You can now test the complete OSINT system!${NC}"

# Keep script running and show real-time logs
echo -e "${BLUE}Showing real-time logs (Ctrl+C to exit):${NC}"
echo "============================================="

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}✅ Services stopped${NC}"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup INT TERM

# Show real-time logs
tail -f logs/backend.log logs/frontend.log