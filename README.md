# ipfs-gateway
a backend API to store files on IPFS written with flask

## Quick Start with Docker

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Start Services

```bash
# Start all services (Flask app, PostgreSQL, Redis)
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Access the Application

- **API**: http://localhost:5000
- **Health Check**: http://localhost:5000/health
- **PostgreSQL**: localhost:5432 (user/pass)
- **Redis**: localhost:6379

### Stop Services

```bash
docker-compose down
```

## Docker Management

The project includes a convenient script for Docker management:

```bash
# Show all available commands
./scripts/docker_manage.sh help

# Manage versions
./scripts/docker_manage.sh version bump minor    # Bump minor version
./scripts/docker_manage.sh version current       # Show current version
./scripts/docker_manage.sh version list          # List all built images

# Build Docker image
./scripts/docker_manage.sh build

# View logs
./scripts/docker_manage.sh logs -f app

# Access container shell
./scripts/docker_manage.sh shell app
```

## Testing Docker Setup

```bash
# Test Docker image build and services
./scripts/test_docker_images.sh

# Full test suite with rebuild
./scripts/test_docker_images.sh --full
```

For complete Docker documentation, see [documentation/DOCKER_SETUP.md](documentation/DOCKER_SETUP.md)
