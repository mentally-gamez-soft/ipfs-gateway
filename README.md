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

## Development Environment Setup

### Prerequisites
- Python 3.13+
- Docker and Docker Compose
- `uv` package manager (recommended) or `pip`

### Initial Setup

1. **Clone the repository and install dependencies**:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
# Copy and edit .env file with your credentials
cp .env.example .env
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: Celery broker URL (typically same as Redis)
- `CELERY_RESULT_BACKEND`: Celery result backend URL
- `FILEBASE_IPFS_API_KEY`: Your Filebase API key
- `FILEBASE_BUCKET`: Your Filebase bucket name
- `S3_ACCESS_KEY`: S3/Filebase access key
- `S3_SECRET_ACCESS_KEY`: S3/Filebase secret key

### Running the Development Environment

**Important**: Before running tests or the application, ensure all required services are running:

1. **Start PostgreSQL and Redis services**:
```bash
# Start database and Redis using Docker Compose
docker compose up -d db redis

# Verify services are healthy
docker compose ps
```

Expected output:
```
NAME                    STATUS
ipfs-gateway-postgres   Up (healthy)
ipfs-gateway-redis      Up (healthy)
```

2. **Start the Celery worker** (in a separate terminal):
```bash
# Start Celery worker for async task processing
celery -A core.celery_app worker --loglevel=info
```

3. **Run database migrations** (first time only):
```bash
alembic upgrade head
```

4. **Start the Flask application**:
```bash
# Development mode
python main.py

# Or using uv
uv run python main.py
```

### Running Tests

**Prerequisites**: Ensure services are running before executing tests:

```bash
# 1. Start required services
docker compose up -d db redis

# 2. Start Celery worker (in separate terminal)
celery -A core.celery_app worker

# 3. Run all tests
uv run python -m pytest tests

# Run specific test suite
uv run python -m pytest tests/e2e/

# Run with coverage
uv run python -m pytest tests --cov=core --cov-report=html

# Run specific test
uv run python -m pytest tests/e2e/test_e2e_filebase_integration.py::TestServiceE2EFilebaseIntegrationAPI::test_api_upload_retrieve_audit_flow -v
```

### Common Development Tasks

```bash
# Check code quality
pre-commit run --all-files

# Run linter
ruff check .

# Format code
ruff format .

# Type checking
mypy core/

# View application logs
tail -f logs/app.log

# Access database directly
docker exec -it ipfs-gateway-postgres psql -U user -d ipfs_gateway

# Monitor Redis
docker exec -it ipfs-gateway-redis redis-cli
```

### Troubleshooting

**Tests failing with "Connection refused" errors**:
- Ensure PostgreSQL and Redis containers are running: `docker compose ps`
- Check services are healthy: `docker compose logs db redis`
- Restart services if needed: `docker compose restart db redis`

**Celery worker not processing tasks**:
- Verify Celery worker is running: `ps aux | grep celery`
- Check Redis connection: `docker exec ipfs-gateway-redis redis-cli ping`
- Review worker logs for errors

**Database connection issues**:
- Verify PostgreSQL is accepting connections: `docker exec ipfs-gateway-postgres pg_isready -U user -d ipfs_gateway`
- Check DATABASE_URL in `.env` matches container settings (localhost:5432)

### Service Ports

- **Flask Application**: 5000
- **PostgreSQL**: 5432
- **Redis**: 6379

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (data will be lost)
docker compose down -v

# Stop Celery worker
# Press Ctrl+C in the terminal where it's running
```
