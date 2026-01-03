# Docker Setup & Local Development Guide

This guide explains how to use Docker and Docker Compose for local development of the IPFS Gateway application.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Docker Components](#docker-components)
5. [Version Management](#version-management)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

## Prerequisites

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- **Git** with git-flow extensions (optional but recommended)
- **Make** (optional, for using Makefile commands)

### Verify Installation

```bash
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ipfs-gateway.git
cd ipfs-gateway
```

### 2. Start All Services

```bash
# Using Docker Compose directly
docker-compose up -d

# Or using the management script
./scripts/docker_manage.sh start
```

### 3. Check Service Status

```bash
docker-compose ps
# or
./scripts/docker_manage.sh status
```

### 4. Access the Application

- **API Base URL**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **PostgreSQL**: localhost:5432 (credentials: user/pass)
- **Redis**: localhost:6379

### 5. Stop Services

```bash
docker-compose down
# or
./scripts/docker_manage.sh stop
```

## Project Structure

```
ipfs-gateway/
├── Dockerfile                 # Development/production image definition
├── docker-compose.yml         # Local dev environment orchestration
├── .dockerignore             # Files excluded from Docker context
├── scripts/
│   ├── docker_manage.sh      # Docker image & container management
│   └── test_docker_images.sh # Docker image validation tests
├── documentation/
│   └── DOCKER_SETUP.md       # This file
├── core/
│   ├── config/settings.py    # App configuration (reads DATABASE_URL_PROD)
│   └── models/connection.py  # Database connection pooling
└── alembic/                  # Database migrations (runs on startup)
```

## Docker Components

### Services Included in docker-compose.yml

#### 1. **app** - Flask Application
- **Image**: Built from `Dockerfile`
- **Port**: 5000
- **Environment**: Development (DEBUG=true, APP_ENV=development)
- **Volumes**: 
  - `.:/app` - Live code reload
  - `./logs:/app/logs` - Persistent log files
- **Features**:
  - Auto-restart on dependency health
  - Database migrations run on startup
  - Gunicorn with reload enabled

#### 2. **db** - PostgreSQL Database
- **Image**: postgres:15-alpine
- **Port**: 5432
- **Credentials**: user/pass
- **Database**: ipfs_gateway
- **Volumes**: `postgres_data:/var/lib/postgresql/data` - Persistent storage
- **Features**:
  - Health checks every 10s
  - Automatic backups (if configured)
  - Connection pooling support

#### 3. **redis** - Cache & Task Queue
- **Image**: redis:7-alpine
- **Port**: 6379
- **Volumes**: `redis_data:/data` - Persistent storage
- **Features**:
  - Append-only file (AOF) persistence
  - Health checks every 10s
  - Used for caching and Celery task queue

### Volumes

```yaml
Volumes:
  postgres_data:    # PostgreSQL database files
  redis_data:       # Redis persistence files
  logs:             # Application logs
```

**Persistence**: These volumes persist between `docker-compose down` and `docker-compose up` calls.

### Networks

```yaml
Networks:
  ipfs-gateway-network:  # Bridge network connecting all services
```

All services communicate through this dedicated network.

## Version Management

### Understanding Semantic Versioning

The project uses semantic versioning format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to the API or architecture
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes and improvements

Example: `1.2.3` = Major version 1, Minor version 2, Patch version 3

### Version Management Commands

Using the `docker_manage.sh` script:

#### Check Current Version

```bash
./scripts/docker_manage.sh version current
# Output: Current version: 0.1.0
```

#### List All Available Versions

```bash
./scripts/docker_manage.sh version list
# Shows all built Docker images with tags
```

#### Set Specific Version

```bash
./scripts/docker_manage.sh version set 1.0.0
```

#### Bump Version

```bash
# Increment patch version (0.1.0 -> 0.1.1)
./scripts/docker_manage.sh version bump fix

# Increment minor version (0.1.0 -> 0.2.0)
./scripts/docker_manage.sh version bump minor

# Increment major version (0.1.0 -> 1.0.0)
./scripts/docker_manage.sh version bump major
```

### Building Images with Versions

```bash
# Build with current version (reads .docker_version file)
./scripts/docker_manage.sh build

# Build with specific version
./scripts/docker_manage.sh build 1.0.0

# Build production image
./scripts/docker_manage.sh build-prod 1.0.0
```

## Common Tasks

### View Application Logs

```bash
# View logs from all services
./scripts/docker_manage.sh logs

# Follow logs in real-time
./scripts/docker_manage.sh logs -f

# View specific service logs
./scripts/docker_manage.sh logs app
./scripts/docker_manage.sh logs db
./scripts/docker_manage.sh logs redis
```

### Access Service Containers

```bash
# Open shell in app container
./scripts/docker_manage.sh shell app

# Open shell in database container
./scripts/docker_manage.sh shell db

# Direct docker-compose exec command
docker-compose exec app bash
docker-compose exec db psql -U user -d ipfs_gateway
```

### Database Operations

```bash
# Connect to PostgreSQL database
docker-compose exec db psql -U user -d ipfs_gateway

# Run database migrations
docker-compose exec app python -m alembic upgrade head

# Reset database (delete all data)
docker-compose exec db dropdb -U user ipfs_gateway
docker-compose exec db createdb -U user ipfs_gateway
```

### Test Database Connectivity

```bash
# From host machine
python scripts/test_db_connection.py

# Or from within app container
docker-compose exec app python scripts/test_db_connection.py
```

### Restart Services

```bash
# Restart all services
./scripts/docker_manage.sh restart

# Restart specific service
docker-compose restart app
docker-compose restart db
docker-compose restart redis
```

### Clean Up Docker Resources

```bash
# Remove stopped containers and dangling images
./scripts/docker_manage.sh clean

# Prune only dangling images
./scripts/docker_manage.sh prune
```

### Health Checks

```bash
# Check service health status
./scripts/docker_manage.sh health

# Or check individual service health
docker-compose exec app curl http://localhost:5000/health
```

## Environment Variables

### Development Environment

Variables used in local development (read from `.env`):

```bash
# Application
APP_ENV=development
DEBUG=true

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@db:5432/ipfs_gateway

# Redis
REDIS_URL=redis://redis:6379/0

# Celery Task Queue
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Filebase IPFS Provider
FILEBASE_BUCKET=your-bucket-name
FILEBASE_ACCESS_KEY=your-access-key
FILEBASE_SECRET_KEY=your-secret-key
```

### Modifying Environment Variables

1. Update `.env` file in the project root
2. Restart services: `./scripts/docker_manage.sh restart`

### Production Environment

For production deployment, use `DATABASE_URL_PROD`:

```bash
DATABASE_URL_PROD=postgresql+psycopg2://user:password@prod-host:5432/ipfs_gateway
```

The application automatically uses the production database when `APP_ENV=production`.

## Troubleshooting

### Services Won't Start

**Problem**: `docker-compose up` fails with error messages

**Solutions**:

1. Check Docker daemon is running
   ```bash
   docker ps
   ```

2. Review logs for errors
   ```bash
   docker-compose logs app
   docker-compose logs db
   ```

3. Ensure ports are not in use
   ```bash
   lsof -i :5000  # Check port 5000
   lsof -i :5432  # Check port 5432
   lsof -i :6379  # Check port 6379
   ```

4. Start with verbose output
   ```bash
   docker-compose up --verbose
   ```

### Database Connection Issues

**Problem**: App container can't connect to PostgreSQL

**Solutions**:

1. Verify database service is running
   ```bash
   docker-compose ps db
   ```

2. Check database health
   ```bash
   docker-compose exec db pg_isready
   ```

3. Verify credentials in `.env`
   ```bash
   # Should see: accepting connections
   docker-compose exec db psql -U user -d ipfs_gateway -c "SELECT 1"
   ```

### Out of Disk Space

**Problem**: `no space left on device` error

**Solutions**:

1. Clean up unused Docker resources
   ```bash
   ./scripts/docker_manage.sh clean
   ```

2. Remove old images
   ```bash
   docker image prune -a  # Remove all unused images
   ```

3. Check disk usage
   ```bash
   docker system df
   docker system prune -a  # Nuclear option: removes all unused resources
   ```

### Application Crashes

**Problem**: App container restarts repeatedly

**Solutions**:

1. Check application logs
   ```bash
   ./scripts/docker_manage.sh logs -f app
   ```

2. Verify all dependencies are installed
   ```bash
   docker-compose exec app pip list
   ```

3. Check for Python syntax errors
   ```bash
   docker-compose exec app python -m py_compile main.py
   ```

### Network Issues

**Problem**: Services can't communicate with each other

**Solutions**:

1. Inspect network
   ```bash
   docker network inspect ipfs-gateway-network
   ```

2. Verify all services are connected
   ```bash
   docker-compose ps
   ```

3. Test connectivity between services
   ```bash
   docker-compose exec app ping db
   docker-compose exec app redis-cli -h redis ping
   ```

## Production Deployment

### Building Production Image

```bash
# Build production image with version
./scripts/docker_manage.sh build-prod 1.0.0

# Or using docker build directly
docker build -t ipfs-gateway:1.0.0-prod \
  --build-arg APP_ENV=production \
  -f Dockerfile.prod .
```

### Production Configuration

Key differences from development:

1. **DEBUG Mode**: Disabled (`DEBUG=false`)
2. **Gunicorn Workers**: Production-optimized (4+ workers)
3. **Volume Mounts**: Code volume removed (no hot reload)
4. **Environment**: `APP_ENV=production`
5. **Database**: Uses `DATABASE_URL_PROD`

### Pushing to Registry

```bash
# Tag image for registry
docker tag ipfs-gateway:1.0.0-prod myregistry.com/ipfs-gateway:1.0.0

# Push to registry
docker push myregistry.com/ipfs-gateway:1.0.0
```

### Deployment on Production Server

```bash
# Pull latest image
docker pull myregistry.com/ipfs-gateway:1.0.0

# Run with appropriate environment variables
docker run -d \
  -p 5000:5000 \
  -e DATABASE_URL_PROD="postgresql://..." \
  -e REDIS_URL="redis://..." \
  -e APP_ENV="production" \
  myregistry.com/ipfs-gateway:1.0.0
```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)
- [Semantic Versioning](https://semver.org/)

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs: `./scripts/docker_manage.sh logs -f app`
3. Create an issue in the repository with:
   - Docker version (`docker --version`)
   - Docker Compose version (`docker-compose --version`)
   - OS information
   - Full error message/logs
   - Steps to reproduce
