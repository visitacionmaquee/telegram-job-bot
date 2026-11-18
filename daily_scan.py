import asyncio
import logging
import os
import sys
from telegram import Bot
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
    DEFAULT_LOCATION,
    DEFAULT_ROLES,
    MIN_MATCH_PERCENT,
    MAX_MATCHES_PER_SCAN,
)
from database import init_db, is_job_seen, mark_job_seen
from scraper import fetch_jobs
from matcher import analyze_job
from bot import format_job_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("daily_scan")

async def run_scan():
    token = os.getenv("TELEGRAM_BOT_TOKEN") or TELEGRAM_BOT_TOKEN
    user_id = os.getenv("TELEGRAM_USER_ID") or TELEGRAM_USER_ID

    if not token or not user_id:
        logger.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID")
        sys.exit(1)

    init_db()
    bot = Bot(token=token)

    logger.info(f"Starting job scan for {DEFAULT_LOCATION}...")
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🔎 Starting job scan across LinkedIn, Indeed & Glassdoor for <b>{DEFAULT_LOCATION}</b>...",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send initial message: {e}")

    qualified_jobs = []
    seen_in_batch = set()

    for role in DEFAULT_ROLES:
        logger.info(f"Scanning role: {role}")
        try:
            raw_jobs = fetch_jobs(search_term=role, location=DEFAULT_LOCATION, results_wanted=6)
            for raw in raw_jobs:
                job_id = raw.get("id")
                if is_job_seen(job_id) or job_id in seen_in_batch:
                    continue
                seen_in_batch.add(job_id)
                analyzed = analyze_job(raw)
                if not analyzed:
                    continue
                if analyzed["match_score"] >= MIN_MATCH_PERCENT:
                    analyzed["job_id"] = job_id
                    qualified_jobs.append(analyzed)
        except Exception as e:
            logger.error(f"Error fetching role '{role}': {e}")

    qualified_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    top_jobs = qualified_jobs[:MAX_MATCHES_PER_SCAN]

    sent_count = 0
    for analyzed in top_jobs:
        try:
            text, reply_markup = format_job_message(analyzed)
            await bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            mark_job_seen(
                job_id=analyzed["job_id"],
                title=analyzed["title"],
                company=analyzed["company"],
                location=analyzed["location"],
                source=analyzed["source"],
                url=analyzed["job_url"],
                match_score=analyzed["match_score"],
                highlight_project=analyzed["highlight_project"],
                stack_match=analyzed["stack_match"]
            )
            sent_count += 1
            await asyncio.sleep(1.5)
        except Exception as e:
            logger.error(f"Error sending job {analyzed.get('title')}: {e}")

    summary_text = (
        f"🎯 Delivered <b>{sent_count}</b> top entry-level match(es) for you!"
        if sent_count > 0
        else "✨ No new junior listings found matching criteria in this scan (duplicates filtered out)."
    )
    try:
        await bot.send_message(chat_id=user_id, text=summary_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send summary message: {e}")

    logger.info(f"Scan finished. Sent {sent_count} jobs.")

if __name__ == "__main__":
    asyncio.run(run_scan())
