import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to PostgreSQL, with automatic SQLite fallback for local development/testing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs_saas.db")

# Fix for Heroku/Render postgres:// URLs (SQLAlchemy requires postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite requires check_same_thread=False
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency that provides an active database session per request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
