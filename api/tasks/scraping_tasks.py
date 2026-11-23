import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from api.celery_app import celery_app
from api.database import SessionLocal
from api import models
from api.services.matcher_service import evaluate_job_match
from scraper import fetch_jobs
from config import DEFAULT_ROLES, DEFAULT_LOCATION

logger = logging.getLogger("celery_tasks")

async def send_telegram_matches(token: str, chat_id: str, matches: List[Dict[str, Any]]):
    """Dispatches matched jobs to Telegram asynchronously"""
    from telegram import Bot
    from bot import format_job_message

    bot = Bot(token=token)
    sent_count = 0
    for analyzed in matches:
        try:
            text, reply_markup = format_job_message(analyzed)
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            sent_count += 1
            await asyncio.sleep(1.2)
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")

    if sent_count > 0:
        await bot.send_message(
            chat_id=chat_id,
            text=f"🎯 Background scan delivered <b>{sent_count}</b> new matching job(s)!",
            parse_mode="HTML"
        )

@celery_app.task(bind=True, name="api.tasks.scraping_tasks.async_scrape_and_match")
def async_scrape_and_match(
    self,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    notify_telegram: bool = False
) -> Dict[str, Any]:
    """
    Celery background worker task:
    Scrapes jobs across LinkedIn, Indeed & Glassdoor,
    evaluates matches against user's candidate profile,
    persists new jobs into PostgreSQL, and optionally notifies via Telegram.
    """
    self.update_state(state="PROGRESS", meta={"progress": 10, "status": "Initializing database and profile..."})

    db = SessionLocal()
    try:
        candidate_profile = None
        target_roles = [role] if role else DEFAULT_ROLES
        target_location = location or DEFAULT_LOCATION
        telegram_chat_id = None

        if user_id:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                telegram_chat_id = user.telegram_chat_id
                if user.profile:
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

        self.update_state(state="PROGRESS", meta={"progress": 30, "status": f"Scraping jobs for {target_location}..."})

        matched_results = []
        seen_ids = set()
        total_scraped = 0

        for r in target_roles[:4]:
            raw_jobs = fetch_jobs(search_term=r, location=target_location, results_wanted=5)
            total_scraped += len(raw_jobs)
            for raw in raw_jobs:
                job_id = raw.get("id")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Persist job if new
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
        top_matches = matched_results[:10]

        self.update_state(state="PROGRESS", meta={"progress": 85, "status": "Dispatching notifications..."})

        # Send Telegram notification if requested and configured
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if notify_telegram and token and telegram_chat_id and top_matches:
            try:
                asyncio.run(send_telegram_matches(token, telegram_chat_id, top_matches))
            except Exception as e:
                logger.warning(f"Telegram dispatch error in worker: {e}")

        return {
            "status": "SUCCESS",
            "total_scraped": total_scraped,
            "matches_count": len(top_matches),
            "top_matches": top_matches
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"Worker task failed: {exc}")
        raise exc
    finally:
        db.close()
