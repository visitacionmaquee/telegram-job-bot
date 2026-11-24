from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.database import init_database
from api.routes import health, users, jobs, applications, tasks, dashboard
from api.metrics import prometheus_middleware, metrics_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_database()
    yield

app = FastAPI(
    title="JobRadar AI — SaaS API",
    description="Multi-tenant AI Job Scraping, Resume Matching & Career Pipeline API",
    version="1.0.0",
    lifespan=lifespan
)

# Prometheus Telemetry Middleware
app.middleware("http")(prometheus_middleware)

# Enable CORS for Next.js / React web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(users.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(applications.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(dashboard.router)

@app.get("/metrics")
def get_metrics():
    """Prometheus telemetry scrape endpoint"""
    return metrics_endpoint()

@app.get("/")
def root():
    return {
        "message": "Welcome to JobRadar AI API",
        "dashboard": "/dashboard",
        "metrics": "/metrics",
        "docs": "/docs",
        "health": "/health"
    }
