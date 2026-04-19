#!/bin/bash
# FinOps Console - Multi-cloud cost management platform
# Startup script for running the application

set -e

echo "🚀 Starting FinOps Console..."
echo "=============================="

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
log_info "Checking prerequisites..."
check_prerequisites() {
    local missing=()
    
    if ! command_exists docker; then
        missing+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing+=("docker-compose")
    fi
    
    if ! command_exists uv; then
        missing+=("uv")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing tools: ${missing[*]}"
        log_info "Please install the missing tools and run this script again."
        exit 1
    fi
    
    log_success "All prerequisites are installed"
}

# Start Docker services
start_docker_services() {
    log_info "Starting Docker services (PostgreSQL, Backend API)..."
    
    cd "$(dirname "$0")"
    
    # Start PostgreSQL and backend
    docker-compose up -d postgres api
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    sleep 10
    
    # Wait for API to be ready
    log_info "Waiting for API server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
            log_success "API is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "API failed to start within timeout"
            exit 1
        fi
        sleep 2
    done
}

# Start frontend development server
start_frontend_dev() {
    log_info "Building and starting frontend..."
    
    # Build frontend
    cd frontend 2>/dev/null || {
        log_info "No frontend directory found, using development mode"
        return 0
    }
    
    # For now, we'll just note the frontend is separate
    log_info "Frontend should be built with: npm run dev"
    log_info "Frontend will be available at http://localhost:5173"
}

# Check backend health
check_backend_health() {
    log_info "Checking backend health..."
    
    for i in {1..20}; do
        if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then
            local health=$(curl -s http://localhost:8000/healthz)
            log_success "Backend is healthy!"
            echo "$health" | head -10
            return 0
        fi
        log_info "Waiting for backend ($i/20)..."
        sleep 2
    done
    
    log_error "Backend health check failed after 20 attempts"
    return 1
}

# Summary and next steps
print_summary() {
    cat << EOF

${GREEN}🎉 FinOps Console is running!${NC}

${BLUE}Backend API:${NC}
  - URL: http://localhost:8000
  - Swagger: http://localhost:8000/docs
  - Health: http://localhost:8000/healthz

${BLUE}Frontend:${NC}
  - URL: http://localhost:5173 (or configured PORT)
  - To start frontend: cd frontend && npm run dev

${BLUE}Default credentials${NC} (for development):
  - Username: admin
  - Password: admin (or check docker-compose.yml)

${BLUE}Quick Links:${NC}
  - Dashboard: http://localhost:5173/dashboard
  - Cost Explorer: http://localhost:5173/explorer
  - Alerts: http://localhost:5173/alerts

${BLUE}To stop the services:${NC}
  cd "$(dirname "$0")" && docker-compose down

${BLUE}To restart:${NC}
  cd "$(dirname "$0")" && docker-compose restart

EOF
}

# Main execution
main() {
    echo "🚀 FinOps Console - Multi-cloud Cost Management Platform"
    echo ""
    
    check_prerequisites
    check_docker_connection
    
    echo ""
    log_info "Starting services..."
    
    start_docker_services
    
    echo ""
    log_info "Running health checks..."
    
    if check_backend_health; then
        print_summary
        log_success "FinOps Console is ready!"
    else
        log_warning "Services started but health check failed"
        print_summary
    fi
}

# Check Docker connection
check_docker_connection() {
    log_info "Checking Docker connection..."
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running or not connected"
        log_info "Please start Docker and run this script again"
        exit 1
    fi
    
    log_success "Docker is running"
}

# Run main
main "$@"
