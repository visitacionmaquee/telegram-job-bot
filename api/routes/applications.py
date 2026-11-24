from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from api.database import get_db
from api import models, schemas

router = APIRouter(prefix="/applications", tags=["Applications & Kanban Board"])

@router.get("", response_model=List[schemas.ApplicationResponse])
def get_applications(
    user_id: int,
    status: Optional[str] = Query(None, description="Filter by status: saved, applied, interview, offer, rejected"),
    db: Session = Depends(get_db)
):
    """Fetch user applications, optionally filtered by Kanban column status"""
    q = db.query(models.Application).filter(models.Application.user_id == user_id)
    if status:
        q = q.filter(models.Application.status == status.lower())
    
    return q.order_by(models.Application.updated_at.desc()).all()

@router.post("", response_model=schemas.ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    user_id: int,
    app_in: schemas.ApplicationCreate,
    db: Session = Depends(get_db)
):
    """Add a job to user's Kanban board (saved, applied, etc.)"""
    # Check if job exists
    job = db.query(models.Job).filter(models.Job.id == app_in.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found in database.")

    # Check if already tracked
    existing = db.query(models.Application).filter(
        models.Application.user_id == user_id,
        models.Application.job_id == app_in.job_id
    ).first()

    if existing:
        # Update existing
        existing.status = app_in.status or existing.status
        if app_in.notes:
            existing.notes = app_in.notes
        db.commit()
        db.refresh(existing)
        return existing

    new_app = models.Application(
        user_id=user_id,
        job_id=app_in.job_id,
        status=app_in.status or "saved",
        match_score=app_in.match_score or 0,
        matched_skills=app_in.matched_skills or [],
        missing_skills=app_in.missing_skills or [],
        highlight_project=app_in.highlight_project,
        quick_pitch=app_in.quick_pitch,
        outreach_linkedin=app_in.outreach_linkedin,
        outreach_email=app_in.outreach_email,
        notes=app_in.notes
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app

@router.patch("/{application_id}", response_model=schemas.ApplicationResponse)
def update_application_status(
    application_id: int,
    app_update: schemas.ApplicationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update application status (Kanban drag-and-drop: saved -> applied -> interview -> offer)
    """
    app_record = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application record not found.")

    if app_update.status:
        valid_statuses = ["saved", "applied", "interview", "offer", "rejected"]
        if app_update.status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{app_update.status}'. Allowed: {', '.join(valid_statuses)}"
            )
        app_record.status = app_update.status.lower()

    if app_update.notes is not None:
        app_record.notes = app_update.notes

    db.commit()
    db.refresh(app_record)
    return app_record

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """Remove application from Kanban tracker"""
    app_record = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail="Application not found.")
    db.delete(app_record)
    db.commit()
    return None

@router.get("/pipeline-stats", response_model=schemas.PipelineStatsResponse)
def get_pipeline_stats(user_id: int, db: Session = Depends(get_db)):
    """Retrieve Kanban summary counts per status column for the dashboard"""
    counts = db.query(
        models.Application.status,
        func.count(models.Application.id)
    ).filter(models.Application.user_id == user_id).group_by(models.Application.status).all()

    stats_map = dict(counts)
    saved = stats_map.get("saved", 0)
    applied = stats_map.get("applied", 0)
    interview = stats_map.get("interview", 0)
    offer = stats_map.get("offer", 0)
    rejected = stats_map.get("rejected", 0)

    return schemas.PipelineStatsResponse(
        saved=saved,
        applied=applied,
        interview=interview,
        offer=offer,
        rejected=rejected,
        total=saved + applied + interview + offer + rejected
    )
