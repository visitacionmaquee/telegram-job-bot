import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "jobs.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                source TEXT,
                url TEXT,
                match_score INTEGER,
                highlight_project TEXT,
                date_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                chat_id TEXT PRIMARY KEY,
                auto_alerts INTEGER DEFAULT 1,
                min_match INTEGER DEFAULT 65,
                custom_roles TEXT DEFAULT '',
                location TEXT DEFAULT 'Philippines'
            )
        """)
    conn.close()

def is_job_seen(job_id: str) -> bool:
    if not job_id:
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_jobs WHERE job_id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def mark_job_seen(job_id: str, title: str, company: str, location: str, source: str, url: str, match_score: int, highlight_project: str):
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO seen_jobs (job_id, title, company, location, source, url, match_score, highlight_project, date_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, title, company, location, source, url, match_score, highlight_project, datetime.utcnow()))
    conn.close()

def get_job_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM seen_jobs")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM seen_jobs WHERE match_score >= 80")
    high_match = cur.fetchone()[0]
    conn.close()
    return {"total": total, "high_match": high_match}
