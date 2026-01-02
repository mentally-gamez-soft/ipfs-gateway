#!/bin/bash

################################################################################
# IPFS Gateway - Docker Image & Container Management Script
# 
# This script provides utilities for managing Docker images and containers
# for the IPFS Gateway application with semantic versioning support.
#
# Usage: ./scripts/docker_manage.sh <command> [options]
#
# Commands:
#   version          - Manage application versions
#   build            - Build Docker image
#   start            - Start all services
#   stop             - Stop all services
#   restart          - Restart all services
#   logs             - View container logs
#   clean            - Clean up unused Docker resources
#   help             - Show this help message
#
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="ipfs-gateway"
IMAGE_NAME="ipfs-gateway"
VERSION_FILE=".docker_version"
DEFAULT_VERSION="0.1.0"

################################################################################
# Helper Functions
################################################################################

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

show_help() {
    cat << EOF
${BLUE}IPFS Gateway - Docker Management${NC}

${YELLOW}Usage:${NC}
  ./scripts/docker_manage.sh <command> [options]

${YELLOW}Commands:${NC}
  version list              List all available versions
  version current           Show current version
  version set <version>     Set/create new version (e.g., 1.0.0)
  version bump <type>       Bump version (major|minor|fix)
  
  build [version]           Build Docker image [with specific version]
  build-prod [version]      Build production Docker image
  
  start                     Start all services (Docker Compose)
  stop                      Stop all services
  restart                   Restart all services
  status                    Show container status
  logs [service]            View logs [of specific service]
  logs -f [service]         Follow logs [of specific service]
  
  shell [service]           Open shell in service container
  clean                     Clean up unused Docker resources
  prune                     Prune dangling images
  
  help                      Show this help message

${YELLOW}Examples:${NC}
  ./scripts/docker_manage.sh version bump minor
  ./scripts/docker_manage.sh build 1.2.0
  ./scripts/docker_manage.sh start
  ./scripts/docker_manage.sh logs -f app
  ./scripts/docker_manage.sh stop

${YELLOW}Environment Variables:${NC}
  DOCKER_REGISTRY           Docker registry URL (default: docker.io)
  DOCKER_USERNAME           Docker registry username
  IMAGE_TAG                 Custom image tag

EOF
}

################################################################################
# Version Management
################################################################################

get_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "$DEFAULT_VERSION"
    fi
}

save_version() {
    echo "$1" > "$VERSION_FILE"
    log_success "Version saved: $1"
}

list_versions() {
    log_info "Available Docker images for ${IMAGE_NAME}:"
    docker images --filter "reference=${IMAGE_NAME}*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" 2>/dev/null || log_warning "No images found"
}

show_current_version() {
    local current=$(get_current_version)
    log_info "Current version: ${GREEN}${current}${NC}"
}

bump_version() {
    local type=$1
    local current=$(get_current_version)
    local IFS='.'
    read -r major minor patch <<< "$current"
    
    case $type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        fix|patch)
            patch=$((patch + 1))
            ;;
        *)
            log_error "Invalid version type: $type (use: major, minor, or fix)"
            return 1
            ;;
    esac
    
    local new_version="${major}.${minor}.${patch}"
    save_version "$new_version"
    log_success "Version bumped to: ${new_version}"
}

set_version() {
    if [[ ! $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format. Use semantic versioning (e.g., 1.0.0)"
        return 1
    fi
    save_version "$1"
}

################################################################################
# Docker Build Operations
################################################################################

build_image() {
    local version=${1:-$(get_current_version)}
    local tag="${IMAGE_NAME}:${version}"
    
    log_info "Building Docker image: ${tag}"
    
    if docker build -t "$tag" -f Dockerfile .; then
        log_success "Image built successfully: ${tag}"
        docker tag "$tag" "${IMAGE_NAME}:latest"
        log_info "Also tagged as: ${IMAGE_NAME}:latest"
        return 0
    else
        log_error "Failed to build Docker image"
        return 1
    fi
}

build_prod_image() {
    local version=${1:-$(get_current_version)}
    local tag="${IMAGE_NAME}:${version}-prod"
    
    log_info "Building production Docker image: ${tag}"
    
    if docker build -t "$tag" \
        --build-arg APP_ENV=production \
        -f Dockerfile.prod .; then
        log_success "Production image built successfully: ${tag}"
        return 0
    else
        log_error "Failed to build production Docker image"
        return 1
    fi
}

################################################################################
# Docker Compose Operations
################################################################################

start_services() {
    log_info "Starting services..."
    
    if docker compose up -d; then
        log_success "Services started"
        sleep 2
        show_status
        return 0
    else
        log_error "Failed to start services"
        return 1
    fi
}

stop_services() {
    log_info "Stopping services..."
    
    if docker compose down; then
        log_success "Services stopped"
        return 0
    else
        log_error "Failed to stop services"
        return 1
    fi
}

restart_services() {
    log_info "Restarting services..."
    stop_services
    sleep 1
    start_services
}

show_status() {
    log_info "Container status:"
    docker compose ps
}

show_logs() {
    local service=$1
    local follow=$2
    
    if [ -z "$service" ]; then
        log_info "Showing logs for all services..."
        if [ "$follow" = "-f" ]; then
            docker compose logs -f
        else
            docker compose logs
        fi
    else
        log_info "Showing logs for service: ${service}"
        if [ "$follow" = "-f" ]; then
            docker compose logs -f "$service"
        else
            docker compose logs "$service"
        fi
    fi
}

shell_service() {
    local service=${1:-app}
    log_info "Opening shell in service: ${service}"
    docker compose exec "$service" bash || docker compose exec "$service" sh
}

################################################################################
# Docker Cleanup Operations
################################################################################

clean_docker() {
    log_warning "Cleaning up Docker resources..."
    log_info "This will remove stopped containers and dangling images"
    
    read -p "Continue? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing stopped containers..."
        docker container prune -f
        
        log_info "Removing dangling images..."
        docker image prune -f
        
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

prune_images() {
    log_warning "Pruning dangling images..."
    
    if docker image prune -f; then
        log_success "Images pruned"
    else
        log_error "Failed to prune images"
        return 1
    fi
}

################################################################################
# Health Checks
################################################################################

health_check() {
    log_info "Checking service health..."
    
    # Check if services are running
    if docker compose ps | grep -q "running"; then
        log_success "Services are running"
        
        # Check API health
        if command -v curl &> /dev/null; then
            log_info "Testing API health endpoint..."
            if curl -s http://localhost:5000/health > /dev/null 2>&1; then
                log_success "API is healthy"
            else
                log_warning "API health check failed"
            fi
        fi
    else
        log_warning "Some services are not running"
        show_status
    fi
}

################################################################################
# Main Script Logic
################################################################################

main() {
    local command=${1:-help}
    local arg1=${2:-}
    local arg2=${3:-}
    
    case "$command" in
        version)
            case "$arg1" in
                list)
                    list_versions
                    ;;
                current)
                    show_current_version
                    ;;
                set)
                    set_version "$arg2"
                    ;;
                bump)
                    bump_version "$arg2"
                    ;;
                *)
                    log_error "Unknown version subcommand: $arg1"
                    show_help
                    exit 1
                    ;;
            esac
            ;;
        build)
            build_image "$arg1"
            ;;
        build-prod)
            build_prod_image "$arg1"
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$arg1" "$arg2"
            ;;
        shell)
            shell_service "$arg1"
            ;;
        clean)
            clean_docker
            ;;
        prune)
            prune_images
            ;;
        health)
            health_check
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
