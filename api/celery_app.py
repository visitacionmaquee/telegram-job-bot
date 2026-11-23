import os
import sys
import socket
from urllib.parse import urlparse
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def check_redis_connection(url: str, timeout: float = 0.4) -> bool:
    """Quick socket check to verify if Redis broker is actively listening"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False

# In-memory broker/backend for tests or local Windows environments without active Redis daemon
is_testing = "pytest" in sys.modules or os.getenv("TESTING") == "1"
is_redis_online = False if is_testing else check_redis_connection(REDIS_URL)

broker_url = REDIS_URL if is_redis_online else "memory://"
backend_url = REDIS_URL if is_redis_online else "cache+memory://"

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
    task_always_eager=not is_redis_online,
    task_eager_propagates=False,
    task_store_eager_result=True,
    task_track_started=True,
    task_time_limit=300,
    broker_connection_retry_on_startup=True
)
