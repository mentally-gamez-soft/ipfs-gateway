"""
Celery configuration for async task processing.
"""
import os
from celery import Celery
from kombu import Queue


def make_celery(app_name=__name__):
    """Create Celery instance."""
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    celery = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=["core.tasks.upload_tasks", "core.tasks.pin_tasks"]
    )
    
    # Configure Celery
    celery.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Task result settings
        result_expires=3600,  # Results expire after 1 hour
        result_persistent=True,
        
        # Task execution settings
        task_acks_late=True,  # Acknowledge task after completion
        task_reject_on_worker_lost=True,
        task_track_started=True,  # Track when task starts
        
        # Retry settings
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,
        
        # Queue settings
        task_default_queue="default",
        task_queues=(
            Queue("default", routing_key="task.#"),
            Queue("upload", routing_key="upload.#"),
            Queue("pin", routing_key="pin.#"),
        ),
        task_default_exchange="tasks",
        task_default_exchange_type="topic",
        task_default_routing_key="task.default",
        
        # Worker settings
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
    )
    
    return celery


# Create celery instance
celery = make_celery("ipfs_gateway")
