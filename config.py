import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9171074042:AAFR3LPksGTaKGvmMfln-roD5y1Br2r1d8Q")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "8880104517")

# Optional Gemini API Key for AI synthesis (falls back to built-in smart engine if blank)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Default Job Search Settings (Explicitly targeting junior, fresh grad & entry level)
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "Philippines")
DEFAULT_ROLES = [
    "Junior Software Engineer",
    "Entry Level Software Engineer",
    "Junior Developer",
    "Junior Python Developer",
    "Junior QA Engineer",
    "Associate Software Engineer",
    "Junior Backend Developer"
]

# Scraping platforms: "linkedin", "indeed", "glassdoor", "zip_recruiter"
DEFAULT_PLATFORMS = ["linkedin", "indeed", "glassdoor"]

# Minimum match percentage to send notification
MIN_MATCH_PERCENT = int(os.getenv("MIN_MATCH_PERCENT", "65"))

# Maximum jobs to send per scan
MAX_MATCHES_PER_SCAN = 10

# Scan schedule: Daily at 8:00 AM PHT (08:00 Asia/Manila)
SCAN_SCHEDULE_PHT_HOURS = [8]
SCAN_INTERVAL_SECONDS = 86400
