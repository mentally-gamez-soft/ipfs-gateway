#!/bin/bash

################################################################################
# Docker Image Test Suite
#
# This script tests Docker image builds and validates that containers
# run correctly with proper service connectivity.
#
# Usage: ./scripts/test_docker_images.sh [--build] [--prod] [--full]
#
# Options:
#   --build         Rebuild images before testing
#   --prod          Test production image
#   --full          Run all tests (build + local + prod)
#   --help          Show this help message
#
################################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="ipfs-gateway"
IMAGE_NAME="ipfs-gateway"
COMPOSE_FILE="docker compose.yml"
TEST_TIMEOUT=60
HEALTH_CHECK_RETRIES=10

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
    ((TESTS_SKIPPED++))
}

show_help() {
    cat << EOF
${BLUE}Docker Image Test Suite${NC}

${YELLOW}Usage:${NC}
  ./scripts/test_docker_images.sh [options]

${YELLOW}Options:${NC}
  --build         Rebuild Docker images before testing
  --prod          Test production image in addition to development
  --full          Run complete test suite (build + all tests)
  --help          Show this help message

${YELLOW}Examples:${NC}
  ./scripts/test_docker_images.sh                # Run existing image tests
  ./scripts/test_docker_images.sh --build        # Rebuild and test
  ./scripts/test_docker_images.sh --prod         # Test production image
  ./scripts/test_docker_images.sh --full         # Complete test suite

EOF
}

test_separator() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

show_summary() {
    echo ""
    test_separator "Test Summary"
    echo -e "Passed:  ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Failed:  ${RED}${TESTS_FAILED}${NC}"
    echo -e "Skipped: ${YELLOW}${TESTS_SKIPPED}${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}${TESTS_FAILED} test(s) failed${NC}"
        return 1
    fi
}

wait_for_endpoint() {
    local url=$1
    local max_attempts=$2
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    return 1
}

################################################################################
# Docker Build Tests
################################################################################

test_build_development_image() {
    test_separator "Test 1: Build Development Image"
    
    log_info "Building development image..."
    
    if docker build -t "${IMAGE_NAME}:test-dev" \
        --build-arg APP_ENV=development \
        -f Dockerfile . > /tmp/docker-build.log 2>&1; then
        log_success "Development image built successfully"
        return 0
    else
        log_error "Failed to build development image"
        tail -n 20 /tmp/docker-build.log
        return 1
    fi
}

test_build_production_image() {
    test_separator "Test 2: Build Production Image"
    
    if [ ! -f "Dockerfile.prod" ]; then
        log_warning "Dockerfile.prod not found, skipping production image build test"
        return 0
    fi
    
    log_info "Building production image..."
    
    if docker build -t "${IMAGE_NAME}:test-prod" \
        --build-arg APP_ENV=production \
        -f Dockerfile.prod . > /tmp/docker-build-prod.log 2>&1; then
        log_success "Production image built successfully"
        return 0
    else
        log_error "Failed to build production image"
        tail -n 20 /tmp/docker-build-prod.log
        return 1
    fi
}

################################################################################
# Docker Compose Tests
################################################################################

test_compose_file() {
    test_separator "Test 3: Validate Docker Compose Configuration"
    
    if docker compose config > /dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
        return 0
    else
        log_error "Invalid Docker Compose configuration"
        docker compose config 2>&1 | head -n 20
        return 1
    fi
}

test_services_start() {
    test_separator "Test 4: Start Services with Docker Compose"
    
    log_info "Starting services..."
    
    if docker compose up -d > /tmp/compose-up.log 2>&1; then
        log_success "Services started successfully"
        sleep 3
        return 0
    else
        log_error "Failed to start services"
        cat /tmp/compose-up.log
        return 1
    fi
}

test_services_running() {
    test_separator "Test 5: Verify Services Are Running"
    
    local services=("app" "db" "redis")
    local all_running=true
    
    for service in "${services[@]}"; do
        if docker compose ps "$service" | grep -q "Up"; then
            log_success "Service '$service' is running"
        else
            log_error "Service '$service' is not running"
            all_running=false
        fi
    done
    
    if [ "$all_running" = true ]; then
        return 0
    else
        docker compose ps
        return 1
    fi
}

################################################################################
# Health Check Tests
################################################################################

test_database_health() {
    test_separator "Test 6: Database Health Check"
    
    log_info "Testing PostgreSQL connectivity..."
    
    if docker compose exec -T db pg_isready -U user > /dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
        return 0
    else
        log_error "PostgreSQL health check failed"
        return 1
    fi
}

test_redis_health() {
    test_separator "Test 7: Redis Health Check"
    
    log_info "Testing Redis connectivity..."
    
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
        return 0
    else
        log_error "Redis health check failed"
        return 1
    fi
}

test_app_health() {
    test_separator "Test 8: Application Health Check"
    
    log_info "Testing application API health endpoint..."
    
    # Wait for app to be ready
    local attempt=0
    while [ $attempt -lt $HEALTH_CHECK_RETRIES ]; do
        if docker compose exec -T app curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            log_success "Application health endpoint is responsive"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log_error "Application health check failed after ${HEALTH_CHECK_RETRIES} attempts"
    return 1
}

################################################################################
# Service Connectivity Tests
################################################################################

test_app_database_connectivity() {
    test_separator "Test 9: App-to-Database Connectivity"
    
    log_info "Testing database connection from app container..."
    
    if docker compose exec -T app python -c "
from sqlalchemy import create_engine
import os
db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Connected successfully')
" > /dev/null 2>&1; then
        log_success "App can connect to database"
        return 0
    else
        log_error "App cannot connect to database"
        return 1
    fi
}

test_app_redis_connectivity() {
    test_separator "Test 10: App-to-Redis Connectivity"
    
    log_info "Testing Redis connection from app container..."
    
    if docker compose exec -T app python -c "
import redis
import os
redis_url = os.getenv('REDIS_URL')
r = redis.from_url(redis_url)
r.ping()
print('Connected successfully')
" > /dev/null 2>&1; then
        log_success "App can connect to Redis"
        return 0
    else
        log_error "App cannot connect to Redis"
        return 1
    fi
}

################################################################################
# Database Migration Tests
################################################################################

test_database_migrations() {
    test_separator "Test 11: Database Migrations"
    
    log_info "Verifying database migrations were run..."
    
    # Check if any tables exist
    if docker compose exec -T db psql -U user -d ipfs_gateway -c "
        SELECT count(*) 
        FROM information_schema.tables 
        WHERE table_schema='public'
    " | grep -q "^[[:space:]]*[1-9]"; then
        log_success "Database tables exist (migrations completed)"
        return 0
    else
        log_warning "No database tables found (migrations may not have run)"
        return 0  # Don't fail this, as migrations might be optional
    fi
}

################################################################################
# Image Validation Tests
################################################################################

test_dev_image_properties() {
    test_separator "Test 12: Development Image Properties"
    
    log_info "Verifying development image properties..."
    
    # Check if Python is available
    if docker run --rm "${IMAGE_NAME}:test-dev" python --version > /dev/null 2>&1; then
        log_success "Python is available in development image"
    else
        log_error "Python is not available in development image"
        return 1
    fi
    
    return 0
}

test_prod_image_properties() {
    test_separator "Test 13: Production Image Properties"
    
    if ! docker images "${IMAGE_NAME}:test-prod" | grep -q "${IMAGE_NAME}"; then
        log_warning "Production image not built, skipping properties test"
        return 0
    fi
    
    log_info "Verifying production image properties..."
    
    # Check if Python is available
    if docker run --rm "${IMAGE_NAME}:test-prod" python --version > /dev/null 2>&1; then
        log_success "Python is available in production image"
    else
        log_error "Python is not available in production image"
        return 1
    fi
    
    return 0
}

################################################################################
# Volume Tests
################################################################################

test_volume_persistence() {
    test_separator "Test 14: Volume Persistence"
    
    log_info "Testing data persistence..."
    
    # Check if volumes exist
    if docker volume inspect postgres_data > /dev/null 2>&1; then
        log_success "PostgreSQL data volume exists"
    else
        log_warning "PostgreSQL data volume not found"
    fi
    
    if docker volume inspect redis_data > /dev/null 2>&1; then
        log_success "Redis data volume exists"
    else
        log_warning "Redis data volume not found"
    fi
    
    return 0
}

################################################################################
# Cleanup Tests
################################################################################

test_services_stop() {
    test_separator "Test 15: Stop Services"
    
    log_info "Stopping services..."
    
    if docker compose down > /tmp/compose-down.log 2>&1; then
        log_success "Services stopped successfully"
        return 0
    else
        log_error "Failed to stop services"
        cat /tmp/compose-down.log
        return 1
    fi
}

################################################################################
# Main Test Suite
################################################################################

run_build_tests() {
    test_build_development_image || return 1
    test_build_production_image || true  # Don't fail if prod image not built
}

run_compose_tests() {
    test_compose_file || return 1
    test_services_start || return 1
    test_services_running || return 1
}

run_health_tests() {
    test_database_health || return 1
    test_redis_health || return 1
    test_app_health || return 1
}

run_connectivity_tests() {
    test_app_database_connectivity || return 1
    test_app_redis_connectivity || return 1
}

run_validation_tests() {
    test_database_migrations || true  # Don't fail if migrations haven't run
    test_dev_image_properties || return 1
    test_prod_image_properties || true  # Don't fail if prod image not built
}

run_integration_tests() {
    test_volume_persistence || return 1
    test_services_stop || return 1
}

################################################################################
# Main Script Entry Point
################################################################################

main() {
    local build_images=false
    local test_production=false
    local test_full=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                build_images=true
                shift
                ;;
            --prod)
                test_production=true
                shift
                ;;
            --full)
                test_full=true
                build_images=true
                test_production=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Print header
    test_separator "IPFS Gateway - Docker Image Test Suite"
    log_info "Build Images: $build_images"
    log_info "Test Production: $test_production"
    
    # Run tests in sequence
    if [ "$build_images" = true ]; then
        run_build_tests || exit 1
    fi
    
    run_compose_tests || exit 1
    run_health_tests || exit 1
    run_connectivity_tests || exit 1
    run_validation_tests || exit 1
    run_integration_tests || exit 1
    
    # Show summary and exit with appropriate code
    show_summary
    exit $?
}

# Run main function
main "$@"
