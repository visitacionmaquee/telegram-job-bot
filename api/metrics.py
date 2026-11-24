import time
from fastapi import Request, Response
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
)

# ----------------- Prometheus Metrics Definitions -----------------

# HTTP Request Telemetry
HTTP_REQUESTS_TOTAL = Counter(
    "jobradar_http_requests_total",
    "Total count of HTTP requests handled by JobRadar API",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION = Histogram(
    "jobradar_http_request_duration_seconds",
    "Histogram of HTTP request durations in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Job Scraping & AI Matching Telemetry
JOBS_SCRAPED_TOTAL = Counter(
    "jobradar_jobs_scraped_total",
    "Total count of jobs scraped from job boards",
    ["source"]
)

JOBS_MATCHED_TOTAL = Counter(
    "jobradar_jobs_matched_total",
    "Total count of jobs matching candidate profile",
    ["role", "quality_tier"]
)

MATCH_SCORE_HISTOGRAM = Histogram(
    "jobradar_match_score_distribution",
    "Distribution of job match scores against candidate profiles",
    buckets=(50, 60, 70, 75, 80, 85, 90, 95, 100)
)

# Application Pipeline Telemetry (Gauges)
APPLICATIONS_GAUGE = Gauge(
    "jobradar_applications_current",
    "Current count of tracked job applications by Kanban stage",
    ["stage"]
)

ACTIVE_USERS_GAUGE = Gauge(
    "jobradar_active_users",
    "Current number of registered SaaS candidates in the database"
)

# Asynchronous Task Queue Telemetry
ASYNC_TASKS_TOTAL = Counter(
    "jobradar_celery_tasks_total",
    "Total Celery asynchronous background tasks dispatched",
    ["task_name", "status"]
)

# ----------------- Prometheus Middleware -----------------

async def prometheus_middleware(request: Request, call_next):
    """Measures request duration and increments Prometheus counters per route"""
    start_time = time.time()
    
    # Clean endpoint path to prevent high cardinality (grouping IDs)
    path = request.url.path
    if path.startswith("/api/v1/users/") and len(path.split("/")) > 4:
        path = "/api/v1/users/{id}/" + path.split("/")[-1]
    elif path.startswith("/api/v1/applications/") and len(path.split("/")) > 4:
        path = "/api/v1/applications/{id}"
    elif path.startswith("/api/v1/tasks/"):
        path = "/api/v1/tasks/{id}"

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
    except Exception as exc:
        status_code = "500"
        raise exc from None
    finally:
        duration = time.time() - start_time
        # Record only non-metrics routes to keep telemetry clean
        if path != "/metrics":
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=path,
                status_code=status_code
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=path
            ).observe(duration)

    return response

def metrics_endpoint():
    """Generates Prometheus scrapable text format metrics"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
