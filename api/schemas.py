from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ----------------- User Schemas -----------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    telegram_chat_id: Optional[str] = None
    tier: Optional[str] = "free"

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    tier: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Candidate Profile Schemas -----------------
class ProfileBase(BaseModel):
    headline: Optional[str] = None
    location: Optional[str] = "Philippines"
    skills: List[str] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    education: Dict[str, Any] = Field(default_factory=dict)
    target_roles: List[str] = Field(default_factory=list)
    min_match_percent: Optional[int] = 65

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Job Schemas -----------------
class JobBase(BaseModel):
    id: str
    title: str
    company: str
    location: str
    source: str
    url: str
    date_posted: Optional[str] = "Recent"
    description: Optional[str] = None

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Application / Kanban Schemas -----------------
class ApplicationBase(BaseModel):
    job_id: str
    status: Optional[str] = "saved"
    match_score: Optional[int] = 0
    highlight_project: Optional[str] = None
    quick_pitch: Optional[str] = None
    outreach_linkedin: Optional[str] = None
    outreach_email: Optional[str] = None
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None # saved, applied, interview, offer, rejected
    notes: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    job: Optional[JobResponse] = None

    model_config = ConfigDict(from_attributes=True)

# ----------------- Pipeline Stats -----------------
class PipelineStatsResponse(BaseModel):
    saved: int = 0
    applied: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0
    total: int = 0
