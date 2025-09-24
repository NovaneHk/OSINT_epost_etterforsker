#!/bin/bash

# OSINT E-post Etterforsker - Integration Test Stop Script
# This script stops both frontend and backend services

echo "🛑 Stopping OSINT E-post Etterforsker Integration Test..."
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to stop service by PID file
stop_service() {
    local service_name=$1
    local pid_file=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo -e "${BLUE}Stopping $service_name (PID: $pid)...${NC}"

        if kill "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ $service_name stopped successfully${NC}"
            rm "$pid_file"
        else
            echo -e "${YELLOW}⚠️  $service_name was not running or already stopped${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Function to stop service by port
stop_by_port() {
    local service_name=$1
    local port=$2

    echo -e "${BLUE}Checking for $service_name on port $port...${NC}"

    local pid=$(lsof -ti:$port)
    if [ -n "$pid" ]; then
        echo -e "${BLUE}Stopping $service_name (PID: $pid) on port $port...${NC}"
        kill "$pid" 2>/dev/null
        sleep 2

        # Force kill if still running
        local still_running=$(lsof -ti:$port)
        if [ -n "$still_running" ]; then
            echo -e "${YELLOW}Force stopping $service_name...${NC}"
            kill -9 "$still_running" 2>/dev/null
        fi

        echo -e "${GREEN}✅ $service_name stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  No $service_name found running on port $port${NC}"
    fi
}

# Create logs directory if it doesn't exist
mkdir -p logs

# Stop services using PID files
echo -e "${BLUE}Stopping services using PID files...${NC}"
stop_service "Backend" "logs/backend.pid"
stop_service "Frontend" "logs/frontend.pid"

# Also check by ports as backup
echo -e "${BLUE}Checking for services by port...${NC}"
stop_by_port "Backend" "8000"
stop_by_port "Frontend" "3000"

# Stop any other related processes
echo -e "${BLUE}Cleaning up any remaining processes...${NC}"

# Kill any Python processes running main.py (backend)
pkill -f "python.*main.py" 2>/dev/null && echo -e "${GREEN}✅ Stopped Python backend processes${NC}" || echo -e "${YELLOW}⚠️  No Python backend processes found${NC}"

# Kill any Node.js processes running Next.js (frontend)
pkill -f "node.*next" 2>/dev/null && echo -e "${GREEN}✅ Stopped Node.js frontend processes${NC}" || echo -e "${YELLOW}⚠️  No Node.js frontend processes found${NC}"

# Clean up log files (optional)
echo -e "${BLUE}Log files:${NC}"
if [ -f "logs/backend.log" ]; then
    echo -e "${BLUE}  Backend log: logs/backend.log ($(wc -l < logs/backend.log) lines)${NC}"
fi

if [ -f "logs/frontend.log" ]; then
    echo -e "${BLUE}  Frontend log: logs/frontend.log ($(wc -l < logs/frontend.log) lines)${NC}"
fi

# Verify ports are free
echo -e "${BLUE}Verifying ports are free...${NC}"
sleep 2

if ! lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Port 8000 (Backend) is free${NC}"
else
    echo -e "${RED}❌ Port 8000 (Backend) is still in use${NC}"
fi

if ! lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Port 3000 (Frontend) is free${NC}"
else
    echo -e "${RED}❌ Port 3000 (Frontend) is still in use${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Integration test environment stopped!${NC}"
echo "============================================="
echo -e "${BLUE}📋 Summary:${NC}"
echo -e "  • Backend (FastAPI) stopped"
echo -e "  • Frontend (Next.js) stopped"
echo -e "  • Ports 8000 and 3000 released"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "  • Log files are preserved in logs/ directory"
echo -e "  • To restart: ./start-integration-test.sh"
echo -e "  • To clean logs: rm logs/*.log"
echo ""
echo -e "${GREEN}✨ Ready for next integration test!${NC}"