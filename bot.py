import logging
import asyncio
import re
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
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
from database import (
    init_db,
    is_job_seen,
    mark_job_seen,
    get_job_stats,
    get_job_by_id,
    track_application,
    get_applications,
    get_pipeline_summary
)
from scraper import fetch_jobs
from matcher import analyze_job, generate_recruiter_note
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
    """Formats job analysis with direct apply, recruiter DM, and application tracking buttons"""
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
    job_id = analyzed.get("job_id", "")

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

    keyboard = [
        [InlineKeyboardButton("🚀 Apply Now ↗", url=url)],
        [
            InlineKeyboardButton("📝 Recruiter DM", callback_data=f"dm:{job_id}"),
            InlineKeyboardButton("⭐ Save", callback_data=f"save:{job_id}"),
            InlineKeyboardButton("✅ Applied", callback_data=f"app:{job_id}")
        ]
    ]
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
        f"🔍 <b>Sources:</b> LinkedIn & Indeed (Entry-Level Only)\n"
        f"⚡ <b>Min Match Alert:</b> {MIN_MATCH_PERCENT}%\n\n"
        f"<b>Available Commands:</b>\n"
        f"• <code>/scan</code> - Trigger a job scan right now\n"
        f"• <code>/search &lt;role&gt; [in &lt;loc&gt;]</code> - Search on-demand\n"
        f"• <code>/saved</code> - View your bookmarked jobs\n"
        f"• <code>/applied</code> - View jobs you have applied for\n"
        f"• <code>/pipeline</code> - View your application status & statistics\n"
        f"• <code>/profile</code> - View your parsed skills & highlight projects\n"
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
            highlight_project=analyzed["highlight_project"],
            stack_match=analyzed["stack_match"]
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

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button clicks for Recruiter DM, Save, and Applied"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("dm:"):
        job_id = data.split("dm:")[1]
        job = get_job_by_id(job_id)
        if not job:
            await query.answer("Job details not found in database.", show_alert=True)
            return
            
        await query.answer("Generated outreach templates!")
        templates = generate_recruiter_note(
            job_title=job["title"],
            company=job["company"],
            highlight_project=job["highlight_project"],
            stack_match=job.get("stack_match", "")
        )
        
        reply = (
            f"📬 <b>Recruiter Outreach Templates</b>\n"
            f"🎯 <b>Role:</b> {job['title']} at {job['company']}\n\n"
            f"🔗 <b>LinkedIn Connection Note</b> (under 300 chars):\n"
            f"<i>Tap below to copy:</i>\n"
            f"<code>{templates['linkedin_note']}</code>\n\n"
            f"✉️ <b>Email / Direct InMail Note:</b>\n"
            f"<code>{templates['email_note']}</code>"
        )
        await query.message.reply_text(reply, parse_mode="HTML")
        
    elif data.startswith("save:"):
        job_id = data.split("save:")[1]
        job = get_job_by_id(job_id)
        if job:
            track_application(job_id, job["title"], job["company"], job["url"], "saved")
            await query.answer("⭐ Job saved to your tracker!", show_alert=False)
            await query.message.reply_text(f"⭐ Saved <b>{job['title']} at {job['company']}</b> to your saved jobs list! View with <code>/saved</code>.", parse_mode="HTML")
        else:
            await query.answer("Job record not found.", show_alert=True)
            
    elif data.startswith("app:"):
        job_id = data.split("app:")[1]
        job = get_job_by_id(job_id)
        if job:
            track_application(job_id, job["title"], job["company"], job["url"], "applied")
            await query.answer("✅ Marked as applied! Good luck!", show_alert=False)
            await query.message.reply_text(f"✅ Marked <b>{job['title']} at {job['company']}</b> as <b>Applied</b>! View pipeline with <code>/pipeline</code>.", parse_mode="HTML")
        else:
            await query.answer("Job record not found.", show_alert=True)

async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /saved command"""
    apps = get_applications(status="saved")
    if not apps:
        await update.message.reply_text("⭐ You have no saved jobs yet! Tap <b>[⭐ Save]</b> on any job alert to bookmark it.", parse_mode="HTML")
        return
        
    msg = f"⭐ <b>Your Saved Jobs ({len(apps)}):</b>\n\n"
    for i, app in enumerate(apps, 1):
        msg += f"{i}. <b>{app['title']}</b> at {app['company']}\n🔗 <a href='{app['url']}'>Apply Link</a>\n\n"
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

async def applied_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /applied command"""
    apps = get_applications(status="applied")
    if not apps:
        await update.message.reply_text("📋 You haven't marked any jobs as applied yet! Tap <b>[✅ Applied]</b> on any job you submit.", parse_mode="HTML")
        return
        
    msg = f"✅ <b>Jobs You've Applied To ({len(apps)}):</b>\n\n"
    for i, app in enumerate(apps, 1):
        msg += f"{i}. <b>{app['title']}</b> at {app['company']}\n🔗 <a href='{app['url']}'>Posting</a>\n\n"
    await update.message.reply_text(msg, parse_mode="HTML", disable_web_page_preview=True)

async def pipeline_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /pipeline command"""
    summary = get_pipeline_summary()
    msg = (
        f"📊 <b>Your Job Application Pipeline:</b>\n\n"
        f"• ⭐ <b>Bookmarked / Saved:</b> {summary['saved']}\n"
        f"• 🚀 <b>Applications Submitted:</b> {summary['applied']}\n"
        f"• 💼 <b>Total Pipeline Tracked:</b> {summary['total']}\n\n"
        f"Use <code>/saved</code> or <code>/applied</code> to view details."
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def scheduled_scan_callback(context: ContextTypes.DEFAULT_TYPE):
    """Periodic background scan executed every SCAN_INTERVAL_SECONDS"""
    if not AUTO_SCAN_ENABLED:
        return
    logger.info("Executing scheduled periodic job scan...")
    await scan_jobs_workflow(TELEGRAM_USER_ID, context)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Lightweight HTTP server so Render Web Service port check passes"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"MakieJob Telegram Bot is alive and running!")

    def log_message(self, format, *args):
        pass # Suppress HTTP access logging in console

def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health check server active on port {port} (Render ready)")
    except Exception as e:
        logger.warning(f"Could not start health check server on port {port}: {e}")

def main():
    """Initializes and runs the Telegram Bot"""
    init_db()
    start_health_server()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("saved", saved_command))
    app.add_handler(CommandHandler("applied", applied_command))
    app.add_handler(CommandHandler("pipeline", pipeline_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("auto", auto_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

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
