import logging
import asyncio
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue
)

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_USER_ID,
    DEFAULT_LOCATION,
    DEFAULT_ROLES,
    MIN_MATCH_PERCENT,
    MAX_MATCHES_PER_SCAN,
    SCAN_INTERVAL_SECONDS
)
from database import init_db, is_job_seen, mark_job_seen, get_job_stats
from scraper import fetch_jobs
from matcher import analyze_job
from resume_profile import CANDIDATE_PROFILE

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# State for automated alerts
AUTO_SCAN_ENABLED = True

def format_job_message(analyzed: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Formats job analysis matching the exact screenshot structure"""
    badge = analyzed["badge"]
    score = analyzed["match_score"]
    title = analyzed["title"]
    company = analyzed["company"]
    location = analyzed["location"]
    source = analyzed["source"]
    posted = analyzed["date_posted"]
    level = analyzed["level"]
    stack = analyzed["stack_match"]
    project = analyzed["highlight_project"]
    pitch = analyzed["quick_pitch"]
    url = analyzed["job_url"]

    # HTML formatted message
    text = (
        f"{badge} <b>[{score}% Match] {title}</b>\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📍 <b>Location:</b> {location} | 🌐 <b>Source:</b> {source}\n"
        f"🕒 <b>Posted:</b> {posted} | 🎓 <b>Level:</b> {level}\n\n"
        f"🛠 <b>Stack Match:</b> {stack}\n"
        f"🏆 <b>Highlight Project:</b> {project}\n"
        f"💡 <b>Quick Pitch:</b> <i>\"{pitch}\"</i>"
    )

    keyboard = [[InlineKeyboardButton("🚀 Apply Now ↗", url=url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return text, reply_markup

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    user_name = CANDIDATE_PROFILE['name']
    welcome_msg = (
        f"👋 <b>Welcome, {user_name}!</b>\n\n"
        f"🎯 <b>Your Job Alert Bot is active & tailored to your resume.</b>\n\n"
        f"📌 <b>Target Roles:</b> {', '.join(DEFAULT_ROLES[:4])}\n"
        f"📍 <b>Location:</b> {DEFAULT_LOCATION}\n"
        f"🔍 <b>Sources:</b> LinkedIn & Indeed\n"
        f"⚡ <b>Min Match Alert:</b> {MIN_MATCH_PERCENT}%\n\n"
        f"<b>Available Commands:</b>\n"
        f"• <code>/scan</code> - Trigger a job scan right now\n"
        f"• <code>/search &lt;role&gt; [location]</code> - Search on-demand (e.g. <code>/search python developer</code>)\n"
        f"• <code>/profile</code> - View your parsed skills & highlight projects\n"
        f"• <code>/stats</code> - View sent and tracked job statistics\n"
        f"• <code>/auto &lt;on/off&gt;</code> - Toggle scheduled background alerts"
    )
    await update.message.reply_text(welcome_msg, parse_mode="HTML")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /profile command"""
    skills_text = ""
    for category, items in CANDIDATE_PROFILE["skills"].items():
        skills_text += f"• <b>{category}:</b> {', '.join(items[:5])}\n"

    projects_text = ""
    for p in CANDIDATE_PROFILE["projects"]:
        projects_text += f"• <b>{p['name']}</b> ({p['role']})\n"

    msg = (
        f"👤 <b>Candidate:</b> {CANDIDATE_PROFILE['name']}\n"
        f"🎓 <b>Education:</b> {CANDIDATE_PROFILE['education']['degree']}\n"
        f"🏫 {CANDIDATE_PROFILE['education']['school']}\n\n"
        f"🛠 <b>Core Skills:</b>\n{skills_text}\n"
        f"🏆 <b>Showcase Projects:</b>\n{projects_text}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def scan_jobs_workflow(chat_id: str, context: ContextTypes.DEFAULT_TYPE, specific_query: str = None, specific_loc: str = None):
    """Scrapes, strictly filters for junior/entry level, sorts by match, and dispatches TOP 10"""
    roles = [specific_query] if specific_query else DEFAULT_ROLES
    location = specific_loc or DEFAULT_LOCATION
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔎 Scanning LinkedIn & Indeed for <b>Entry-Level / Junior</b> tech roles in <b>{location}</b>...",
        parse_mode="HTML"
    )

    qualified_jobs = []
    seen_in_batch = set()

    for role in roles:
        try:
            raw_jobs = fetch_jobs(search_term=role, location=location, results_wanted=6)
            for raw in raw_jobs:
                job_id = raw.get("id")
                
                # Check DB and in-batch duplicates
                if is_job_seen(job_id) or job_id in seen_in_batch:
                    continue
                    
                seen_in_batch.add(job_id)
                analyzed = analyze_job(raw)
                
                # Filtered out if non-junior (analyze_job returns None)
                if not analyzed:
                    continue
                
                # Minimum match threshold
                if analyzed["match_score"] >= MIN_MATCH_PERCENT:
                    analyzed["job_id"] = job_id
                    qualified_jobs.append(analyzed)
                    
        except Exception as e:
            logger.error(f"Error scanning role '{role}': {e}")

    # Sort descending by match score to get the absolute best matches
    qualified_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    top_jobs = qualified_jobs[:MAX_MATCHES_PER_SCAN]

    sent_count = 0
    for analyzed in top_jobs:
        text, reply_markup = format_job_message(analyzed)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
        
        # Mark seen in SQLite
        mark_job_seen(
            job_id=analyzed["job_id"],
            title=analyzed["title"],
            company=analyzed["company"],
            location=analyzed["location"],
            source=analyzed["source"],
            url=analyzed["job_url"],
            match_score=analyzed["match_score"],
            highlight_project=analyzed["highlight_project"]
        )
        sent_count += 1
        await asyncio.sleep(1.5) # Anti-flood delay

    if sent_count > 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎯 Delivered <b>{sent_count}</b> top entry-level / junior match(es) for you!",
            parse_mode="HTML"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✨ No new entry-level listings found in this scan cycle. Deduplication prevented repeats. Will scan again on schedule!",
            parse_mode="HTML"
        )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for manual /scan command"""
    chat_id = str(update.effective_chat.id)
    await scan_jobs_workflow(chat_id, context)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /search <role> [in <location>]"""
    if not context.args:
        await update.message.reply_text(
            "💡 <b>Usage:</b>\n"
            "• <code>/search Python Developer</code>\n"
            "• <code>/search QA Engineer in Makati</code>\n"
            "• <code>/search Cloud Engineer Remote</code>",
            parse_mode="HTML"
        )
        return
        
    full_arg = " ".join(context.args).strip()
    
    # Check if user used " in " delimiter, e.g. "Software Engineer in Makati"
    if " in " in full_arg.lower():
        parts = re.split(r'\s+in\s+', full_arg, flags=re.IGNORECASE)
        query = parts[0].strip()
        loc = parts[1].strip() if len(parts) > 1 else DEFAULT_LOCATION
    else:
        # Check if the last word is a common location
        words = full_arg.split()
        known_locations = ["remote", "makati", "manila", "cebu", "taguig", "pasig", "quezon", "philippines", "bulacan", "worldwide", "usa"]
        if len(words) > 1 and words[-1].lower() in known_locations:
            query = " ".join(words[:-1])
            loc = words[-1]
        else:
            query = full_arg
            loc = DEFAULT_LOCATION
            
    chat_id = str(update.effective_chat.id)
    await scan_jobs_workflow(chat_id, context, specific_query=query, specific_loc=loc)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command"""
    stats = get_job_stats()
    await update.message.reply_text(
        f"📊 <b>Job Alert Bot Stats:</b>\n\n"
        f"• Total Listings Tracked: <b>{stats['total']}</b>\n"
        f"• High Match (80%+): <b>{stats['high_match']}</b>\n"
        f"• Scan Interval: Every <b>{SCAN_INTERVAL_SECONDS // 3600} hours</b>\n"
        f"• Auto-Alerts: <b>{'Enabled' if AUTO_SCAN_ENABLED else 'Disabled'}</b>",
        parse_mode="HTML"
    )

async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /auto on or /auto off"""
    global AUTO_SCAN_ENABLED
    if not context.args:
        status_str = "Enabled" if AUTO_SCAN_ENABLED else "Disabled"
        await update.message.reply_text(f"Auto-alerts currently: <b>{status_str}</b>\nUse <code>/auto on</code> or <code>/auto off</code> to change.", parse_mode="HTML")
        return

    arg = context.args[0].lower()
    if arg == "on":
        AUTO_SCAN_ENABLED = True
        await update.message.reply_text("🔔 <b>Auto-alerts ENABLED.</b> You will receive periodic scans automatically.", parse_mode="HTML")
    elif arg == "off":
        AUTO_SCAN_ENABLED = False
        await update.message.reply_text("🔕 <b>Auto-alerts DISABLED.</b> You can still use <code>/scan</code> or <code>/search</code> manually.", parse_mode="HTML")
    else:
        await update.message.reply_text("Usage: <code>/auto on</code> or <code>/auto off</code>", parse_mode="HTML")

async def scheduled_scan_callback(context: ContextTypes.DEFAULT_TYPE):
    """Periodic background scan executed every SCAN_INTERVAL_SECONDS"""
    if not AUTO_SCAN_ENABLED:
        return
    logger.info("Executing scheduled periodic job scan...")
    await scan_jobs_workflow(TELEGRAM_USER_ID, context)

def main():
    """Initializes and runs the Telegram Bot"""
    init_db()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("auto", auto_command))

    # Add periodic background task
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            scheduled_scan_callback,
            interval=SCAN_INTERVAL_SECONDS,
            first=10 # First scan starts 10 seconds after bot boot
        )

    logger.info("Bot starting up...")
    app.run_polling()

if __name__ == "__main__":
    main()
