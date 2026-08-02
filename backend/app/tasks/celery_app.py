from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "botforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.document_tasks", "app.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-email-inbox": {
        "task": "app.tasks.email_tasks.check_inbox",
        "schedule": 60.0,  # Every 60 seconds
    },
}
