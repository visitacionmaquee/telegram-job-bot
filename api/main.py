from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.database import init_database
from api.routes import health, users, jobs, applications

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

@app.get("/")
def root():
    return {
        "message": "Welcome to JobRadar AI API",
        "docs": "/docs",
        "health": "/health"
    }
