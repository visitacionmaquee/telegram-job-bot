from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/users", tags=["Users & Profiles"])

@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new SaaS user or retrieve existing by email"""
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    user = models.User(
        email=user_in.email,
        full_name=user_in.full_name,
        telegram_chat_id=user_in.telegram_chat_id,
        tier=user_in.tier or "free"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize empty profile for user
    profile = models.CandidateProfile(user_id=user.id)
    db.add(profile)
    db.commit()

    return user

@router.get("/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Fetch user by ID"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

@router.get("/{user_id}/profile", response_model=schemas.ProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """Retrieve candidate profile (skills, projects, target roles)"""
    profile = db.query(models.CandidateProfile).filter(models.CandidateProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found for this user.")
    return profile

@router.put("/{user_id}/profile", response_model=schemas.ProfileResponse)
def update_user_profile(user_id: int, profile_in: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    """Update skills, projects, education, and target roles for custom job matching"""
    profile = db.query(models.CandidateProfile).filter(models.CandidateProfile.user_id == user_id).first()
    if not profile:
        profile = models.CandidateProfile(user_id=user_id)
        db.add(profile)

    update_data = profile_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile
