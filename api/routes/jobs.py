from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db
from api import models, schemas
from api.services.matcher_service import evaluate_job_match
from scraper import fetch_jobs
from config import DEFAULT_ROLES, DEFAULT_LOCATION

router = APIRouter(prefix="/jobs", tags=["Jobs & Scraping"])

@router.get("", response_model=List[schemas.JobResponse])
def list_jobs(
    query: Optional[str] = None,
    location: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieve catalog of scraped jobs with optional filtering"""
    q = db.query(models.Job)
    if query:
        q = q.filter(models.Job.title.ilike(f"%{query}%"))
    if location:
        q = q.filter(models.Job.location.ilike(f"%{location}%"))
    if source:
        q = q.filter(models.Job.source.ilike(f"%{source}%"))

    jobs = q.order_by(models.Job.created_at.desc()).offset(offset).limit(limit).all()
    return jobs

@router.post("/scan", response_model=List[dict])
def trigger_job_scan(
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Triggers scraper across LinkedIn, Indeed & Glassdoor,
    evaluates match scores against candidate profile, saves jobs,
    and returns top matches.
    """
    candidate_profile = None
    target_roles = [role] if role else DEFAULT_ROLES
    target_location = location or DEFAULT_LOCATION

    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user and user.profile:
            candidate_profile = {
                "skills": user.profile.skills or [],
                "projects": user.profile.projects or [],
                "education": user.profile.education or {},
                "min_match_percent": user.profile.min_match_percent or 65
            }
            if user.profile.target_roles and not role:
                target_roles = user.profile.target_roles
            if user.profile.location and not location:
                target_location = user.profile.location

    matched_results = []
    seen_ids = set()

    for r in target_roles[:4]: # Limit batch for API responsiveness
        raw_jobs = fetch_jobs(search_term=r, location=target_location, results_wanted=5)
        for raw in raw_jobs:
            job_id = raw.get("id")
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Persist or update job in DB
            existing_job = db.query(models.Job).filter(models.Job.id == job_id).first()
            if not existing_job:
                new_job = models.Job(
                    id=job_id,
                    title=raw.get("title", ""),
                    company=raw.get("company", ""),
                    location=raw.get("location", target_location),
                    source=raw.get("site", "linkedin"),
                    url=raw.get("job_url", ""),
                    date_posted=str(raw.get("date_posted", "Recent")),
                    description=raw.get("description", "")
                )
                db.add(new_job)

            # Evaluate AI match
            evaluated = evaluate_job_match(raw, candidate_profile)
            if evaluated:
                min_threshold = candidate_profile.get("min_match_percent", 65) if candidate_profile else 65
                if evaluated["match_score"] >= min_threshold:
                    matched_results.append(evaluated)

    db.commit()

    # Sort descending by match score
    matched_results.sort(key=lambda x: x["match_score"], reverse=True)
    return matched_results[:10]

@router.post("/scan-async")
def trigger_job_scan_async(
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    notify_telegram: bool = True
):
    """
    Enqueues an asynchronous background job scan using Celery & Redis.
    Instantly returns a task_id that can be polled via /api/v1/tasks/{task_id}.
    Gracefully handles environments without active Redis daemon by running in a background worker thread.
    """
    import uuid
    from threading import Thread
    from api.celery_app import is_redis_online
    from api.tasks.scraping_tasks import async_scrape_and_match

    task_id = str(uuid.uuid4())

    if is_redis_online:
        task = async_scrape_and_match.apply_async(
            kwargs={
                "user_id": user_id,
                "role": role,
                "location": location,
                "notify_telegram": notify_telegram
            },
            task_id=task_id
        )
    else:
        thread = Thread(
            target=async_scrape_and_match.apply,
            kwargs={
                "kwargs": {
                    "user_id": user_id,
                    "role": role,
                    "location": location,
                    "notify_telegram": notify_telegram
                },
                "task_id": task_id
            },
            daemon=True
        )
        thread.start()

    return {
        "task_id": task_id,
        "status": "QUEUED",
        "message": "Background job scan enqueued successfully.",
        "poll_url": f"/api/v1/tasks/{task_id}"
    }
