#!/usr/bin/env bash
#
# Start Celery worker for IPFS Gateway
#
# Usage: ./start_worker.sh

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting Celery worker..."
echo "Broker: ${CELERY_BROKER_URL}"
echo "Backend: ${CELERY_RESULT_BACKEND}"

# Start Celery worker with autoreload for development
celery -A core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=solo \
    --beat
