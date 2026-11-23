from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from api.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    telegram_chat_id = Column(String(64), unique=True, index=True, nullable=True)
    tier = Column(String(32), default="free")  # "free" or "pro"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    headline = Column(String(255), nullable=True)
    location = Column(String(255), default="Philippines")
    skills = Column(JSON, default=list)  # ["Python", "Docker", "PostgreSQL", ...]
    projects = Column(JSON, default=list) # [{"name": "...", "summary": "...", ...}]
    education = Column(JSON, default=dict) # {"degree": "...", "school": "...", ...}
    target_roles = Column(JSON, default=list) # ["Junior Software Engineer", "Python Developer"]
    min_match_percent = Column(Integer, default=65)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True) # MD5 hash
    title = Column(String(255), index=True, nullable=False)
    company = Column(String(255), index=True, nullable=False)
    location = Column(String(255), index=True, nullable=False)
    source = Column(String(64), index=True, nullable=False) # linkedin, indeed, glassdoor
    url = Column(Text, nullable=False)
    date_posted = Column(String(64), default="Recent")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), default="saved", index=True) # saved, applied, interview, offer, rejected
    match_score = Column(Integer, default=0)
    highlight_project = Column(String(255), nullable=True)
    quick_pitch = Column(Text, nullable=True)
    outreach_linkedin = Column(Text, nullable=True)
    outreach_email = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
