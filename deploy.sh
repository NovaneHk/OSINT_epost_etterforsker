
#!/bin/bash

# OSINT E-post Etterforsker - Production Deployment Script
# This script handles the complete deployment of the OSINT system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="osint-etterforsker"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"
LOG_DIR="./logs"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}===============================================${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"

    # Check if required files exist
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    print_success "Docker Compose file found"

    print_success "All prerequisites satisfied"
}

# Function to create directories
create_directories() {
    print_header "CREATING DIRECTORIES"

    local dirs=("$BACKUP_DIR" "$LOG_DIR" "nginx/ssl" "nginx/logs" "monitoring" "data")

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        else
            print_status "Directory already exists: $dir"
        fi
    done

    print_success "All directories created"
}

# Function to handle environment file
setup_environment() {
    print_header "SETTING UP ENVIRONMENT"

    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        print_status "Creating environment file from template..."

        # Copy from .env.example if it exists
        if [ -f ".env.example" ]; then
            cp ".env.example" "$ENV_FILE"
            print_warning "Created $ENV_FILE from .env.example"
            print_warning "Please update the production values in $ENV_FILE before continuing!"
            read -p "Press Enter when you have updated the environment file..."
        else
            print_error "No environment template found. Please create $ENV_FILE manually."
            exit 1
        fi
    else
        print_success "Environment file found: $ENV_FILE"
    fi

    # Check for default passwords
    if grep -q "CHANGE_THIS" "$ENV_FILE"; then
        print_warning "Default passwords detected in $ENV_FILE"
        print_warning "Please update all CHANGE_THIS values before production deployment!"

        read -p "Have you updated all passwords? (yes/no): " -r
        if [[ ! $REPLY =~ ^yes$ ]]; then
            print_error "Please update all passwords in $ENV_FILE before continuing"
            exit 1
        fi
    fi

    print_success "Environment configuration verified"
}

# Function to build images
build_images() {
    print_header "BUILDING DOCKER IMAGES"

    print_status "Building images with Docker Compose..."

    if docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" build --no-cache; then
        print_success "All images built successfully"
    else
        print_error "Failed to build images"
        exit 1
    fi
}

# Function to start services
start_services() {
    print_header "STARTING SERVICES"

    print_status "Starting services with Docker Compose..."

    if docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" up -d; then
        print_success "All services started successfully"
    else
        print_error "Failed to start services"
        exit 1
    fi
}

# Function to wait for services to be healthy
wait_for_services() {
    print_header "WAITING FOR SERVICES TO BE READY"

    local services=("database" "redis" "backend" "frontend")
    local max_attempts=30
    local attempt=1

    for service in "${services[@]}"; do
        print_status "Waiting for $service to be healthy..."

        while [ $attempt -le $max_attempts ]; do
            if docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" ps "$service" | grep -q "healthy"; then
                print_success "$service is healthy"
                break
            elif [ $attempt -eq $max_attempts ]; then
                print_error "$service failed to become healthy"
                docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" logs "$service"
                exit 1
            fi

            print_status "Attempt $attempt/$max_attempts - $service not ready yet..."
            sleep 10
            attempt=$((attempt + 1))
        done
        attempt=1
    done

    print_success "All services are healthy"
}

# Function to run database migrations
run_migrations() {
    print_header "RUNNING DATABASE MIGRATIONS"

    print_status "Running Alembic migrations..."

    if docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" exec -T backend alembic upgrade head; then
        print_success "Database migrations completed"
    else
        print_warning "Migration failed or no migrations to run"
        print_status "Checking if tables exist..."

        # Try to create tables manually if migrations fail
        docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" exec -T backend python -c "
import asyncio
from backend.core.database import create_tables
asyncio.run(create_tables())
print('Tables created successfully')
        " || print_warning "Could not create tables automatically"
    fi
}

# Function to verify deployment
verify_deployment() {
    print_header "VERIFYING DEPLOYMENT"

    # Check if all containers are running
    print_status "Checking container status..."
    docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" ps

    # Test API endpoints
    print_status "Testing API endpoints..."

    local backend_url="http://localhost:8000"
    local frontend_url="http://localhost:3000"

    # Test backend health
    if curl -f -s "$backend_url/health" > /dev/null; then
        print_success "Backend health check passed"
    else
        print_error "Backend health check failed"
        exit 1
    fi

    # Test frontend
    if curl -f -s "$frontend_url" > /dev/null; then
        print_success "Frontend accessibility check passed"
    else
        print_error "Frontend accessibility check failed"
        exit 1
    fi

    print_success "Deployment verification completed"
}

# Function to show deployment summary
show_summary() {
    print_header "DEPLOYMENT SUMMARY"

    echo -e "${CYAN}🎉 OSINT E-post Etterforsker deployed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📱 Frontend:${NC} http://localhost:3000"
    echo -e "${BLUE}🔧 Backend API:${NC} http://localhost:8000"
    echo -e "${BLUE}📚 API Documentation:${NC} http://localhost:8000/docs"
    echo -e "${BLUE}❤️ Health Check:${NC} http://localhost:8000/health"
    echo -e "${BLUE}📊 Grafana Monitoring:${NC} http://localhost:3001"
    echo -e "${BLUE}📈 Prometheus Metrics:${NC} http://localhost:9090"
    echo ""
    echo -e "${YELLOW}📋 Management Commands:${NC}"
    echo -e "  View logs: docker-compose logs -f"
    echo -e "  Stop services: docker-compose down"
    echo -e "  Restart services: docker-compose restart"
    echo -e "  Database backup: ./database/backup-restore.sh full"
    echo ""
    echo -e "${YELLOW}🛑 Important Security Notes:${NC}"
    echo -e "  • Change all default passwords in production"
    echo -e "  • Configure SSL/TLS certificates"
    echo -e "  • Set up proper firewall rules"
    echo -e "  • Enable monitoring and alerting"
    echo -e "  • Schedule regular backups"
    echo ""
    echo -e "${GREEN}✨ System is ready for use!${NC}"
}

# Function to handle cleanup on failure
cleanup_on_failure() {
    print_error "Deployment failed. Cleaning up..."
    docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" down --remove-orphans
    exit 1
}

# Function to stop services
stop_services() {
    print_header "STOPPING SERVICES"

    print_status "Stopping all services..."

    if docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" down; then
        print_success "All services stopped"
    else
        print_error "Failed to stop some services"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    local service="${1:-}"

    if [ -n "$service" ]; then
        print_status "Showing logs for service: $service"
        docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" logs -f "$service"
    else
        print_status "Showing logs for all services"
        docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" logs -f
    fi
}

# Function to show status
show_status() {
    print_header "SYSTEM STATUS"

    print_status "Container status:"
    docker-compose --env-file "$ENV_FILE" -f "$DOCKER_COMPOSE_FILE" ps

    echo ""
    print_status "Resource usage:"
    docker stats --no-stream
}

# Trap for cleanup on failure
trap cleanup_on_failure ERR

# Main execution logic
case "${1:-deploy}" in
    "deploy")
        print_header "OSINT E-POST ETTERFORSKER - PRODUCTION DEPLOYMENT"
        echo -e "${CYAN}Starting deployment process...${NC}"
        echo ""

        check_prerequisites
        create_directories
        setup_environment
        build_images
        start_services
        wait_for_services
        run_migrations
        verify_deployment
        show_summary
        ;;

    "stop")
        stop_services
        ;;
