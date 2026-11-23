import os
import sys
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Use in-memory broker/backend for tests or local environments without active Redis
is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "1"
broker_url = "memory://" if is_testing else REDIS_URL
backend_url = "cache+memory://" if is_testing else REDIS_URL

celery_app = Celery(
    "jobradar_worker",
    broker=broker_url,
    backend=backend_url,
    include=["api.tasks.scraping_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Manila",
    enable_utc=True,
    task_always_eager=is_testing,
    task_eager_propagates=is_testing,
    task_store_eager_result=is_testing,
    task_track_started=True,
    task_time_limit=300,
    broker_connection_retry_on_startup=True
)
