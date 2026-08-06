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
    # Celery's default is to retry a failed broker connection up to 100 times
    # with backoff before giving up — on a deploy with no Redis at all (the
    # free portfolio path), that turns every single `.delay()` call in the API
    # process into a 60-90+ second stall before it finally raises. Routers that
    # dispatch tasks (see knowledge.py's _dispatch_or_run_inline) already catch
    # that failure and fall back to processing the work inline, but the
    # fallback is only useful if the failure itself is fast. Disabling retry
    # here makes `.delay()` fail immediately when no broker is reachable, and
    # has no effect once Redis actually is configured — connections just
    # succeed instead.
    broker_connection_retry=False,
    broker_connection_retry_on_startup=False,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-email-inbox": {
        "task": "app.tasks.email_tasks.check_inbox",
        "schedule": 60.0,  # Every 60 seconds
    },
}
