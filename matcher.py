import re
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, date
import requests
from resume_profile import CANDIDATE_PROFILE
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

ALL_CANDIDATE_SKILLS = [
    # Languages & Core
    "Python", "Node.js", "SQL", "JavaScript", "TypeScript", "Bash", "Shell",
    # Databases
    "PostgreSQL", "Database Management", "Data Integrity",
    # DevOps, Cloud & OS
    "Docker", "Oracle Cloud", "Linux", "Containerization", "Cloud", "CI/CD",
    # Observability & IoT
    "Prometheus", "Grafana", "Telemetry", "Observability", "Hardware", "IoT", "Monitoring",
    # Testing & QA
    "Postman", "Selenium", "Automated QA", "Manual QA", "API Testing", "UAT",
    # Architecture
    "RESTful APIs", "REST APIs", "REST", "Git", "Microservices"
]

SENIOR_DISQUALIFIERS = [
    r'\bsenior\b', r'\bsr\b', r'\bsr\.\b', r'\blead\b', r'\bprincipal\b',
    r'\barchitect\b', r'\bmanager\b', r'\bdirector\b', r'\bhead\b', r'\bstaff\b',
    r'\btech lead\b', r'\bteam lead\b', r'\bii\b', r'\biii\b', r'\biv\b',
    r'\bmid-senior\b', r'\bintermediate\b', r'\bexpert\b', r'\bvp\b'
]

EXPERIENCE_DISQUALIFIERS = [
    r'\b([3-9]|\d{2})\+?\s*(years|yrs|year)\s*(of)?\s*(experience|exp|hands-on)?\b',
    r'\bat least (3|4|5|6|7|8|9|10) years\b',
    r'\bminimum (3|4|5|6|7|8|9|10) years\b',
    r'\b(3|4|5|6|7|8|9|10)\s*-\s*\d+\s*years\b'
]

ENTRY_POSITIVE_SIGNALS = [
    r'\bjr\b', r'\bjr\.\b', r'\bjunior\b', r'\bassociate\b', r'\bentry level\b',
    r'\bentry-level\b', r'\bfresh grad\b', r'\bfresh graduate\b', r'\bgraduate\b',
    r'\btrainee\b', r'\bintern\b', r'\binternship\b', r'\b0-1\b', r'\b0-2\b',
    r'\bno experience\b', r'\brecent graduate\b'
]

def is_recent_post(date_val: Any, max_days: int = 90) -> bool:
    """Returns True if the posting is newer than max_days (default 90 days / ~3 months)"""
    if not date_val:
        return True
        
    date_str = str(date_val).strip().lower()
    
    # 1. Reject year(s)
    if "year" in date_str or ("yr" in date_str and "ago" in date_str):
        return False
        
    # 2. Reject 3+ months ago
    m_month = re.search(r'(\d+)\+?\s*month', date_str)
    if m_month:
        months = int(m_month.group(1))
        if months >= 3:
            return False
        return True
        
    # 3. Reject >= 13 weeks (~90 days)
    m_week = re.search(r'(\d+)\+?\s*week', date_str)
    if m_week:
        weeks = int(m_week.group(1))
        if weeks >= 13:
            return False
        return True
        
    # 4. Reject > 90 days ago
    m_day = re.search(r'(\d+)\+?\s*day', date_str)
    if m_day:
        days = int(m_day.group(1))
        if days > max_days:
            return False
        return True
        
    # 5. Parse absolute date formats (e.g. 2026-10-31)
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"]:
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            diff_days = (datetime.now().date() - parsed).days
            if diff_days > max_days:
                return False
            return True
        except ValueError:
            continue

    return True

def is_junior_or_entry_level(title: str, description: str) -> bool:
    """Strictly checks if job is junior/entry-level/fresh-grad friendly"""
    title_lower = title.lower()
    desc_lower = (description or "").lower()
    
    # 1. Immediately eliminate senior titles
    for pattern in SENIOR_DISQUALIFIERS:
        if re.search(pattern, title_lower):
            return False
            
    # 2. Eliminate jobs demanding 3+ years experience in description
    for pattern in EXPERIENCE_DISQUALIFIERS:
        if re.search(pattern, desc_lower) or re.search(pattern, title_lower):
            # Only allow if explicitly says "junior" or "entry" in title
            if not any(re.search(p, title_lower) for p in [r'\bjunior\b', r'\bjr\b', r'\bentry\b']):
                return False

    return True

def determine_experience_level(title: str, description: str) -> str:
    text = (title + " " + (description or "")).lower()
    
    if any(k in text for k in ["fresh grad", "fresh graduate", "recent graduate", "0-1 yr", "0-1 year"]):
        return "Fresh Grad / 0-1 yr"
    if any(k in text for k in ["junior", "jr", "associate", "intern", "internship", "trainee", "graduate"]):
        return "Junior / Entry Level"
    if any(k in text for k in ["0-2 years", "1-2 years", "1-2 yrs", "entry level", "entry-level"]):
        return "Entry Level (0-2 yrs)"
        
    return "Entry Level / Junior (Unspecified)"

def extract_stack_matches(text: str) -> List[str]:
    text_lower = text.lower()
    matches = []
    
    skill_mapping = {
        "python": "Python",
        "node": "Node.js",
        "node.js": "Node.js",
        "sql": "SQL",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "docker": "Docker",
        "linux": "Linux",
        "rest": "REST APIs",
        "restful": "REST APIs",
        "api": "REST APIs",
        "git": "Git",
        "postman": "Postman",
        "selenium": "Selenium",
        "qa": "QA Testing",
        "testing": "QA Testing",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "telemetry": "Telemetry / Observability",
        "iot": "IoT",
        "oracle cloud": "Oracle Cloud",
        "cloud": "Cloud Computing",
        "ci/cd": "CI/CD",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
    }
    
    for needle, clean_name in skill_mapping.items():
        # Word boundary match
        pattern = r'\b' + re.escape(needle) + r'\b'
        if re.search(pattern, text_lower):
            if clean_name not in matches:
                matches.append(clean_name)
                
    return matches

def select_highlight_project(job_title: str, matched_skills: List[str], description: str) -> Dict[str, Any]:
    text = (job_title + " " + " ".join(matched_skills) + " " + (description or "")).lower()
    
    # Check QA / Testing first
    qa_patterns = [r'\bqa\b', r'\btester\b', r'\btesting\b', r'\bselenium\b', r'\bpostman\b', r'\bquality assurance\b', r'\btest engineer\b']
    if any(re.search(p, text) for p in qa_patterns):
        return CANDIDATE_PROFILE["projects"][1] # E-Commerce QA Suite
    
    # Check Web / UI / Frontend
    web_patterns = [r'\bfrontend\b', r'\bfront-end\b', r'\bui\b', r'\bux\b', r'\bweb developer\b', r'\bwordpress\b', r'\breact\b', r'\bhtml\b']
    if any(re.search(p, text) for p in web_patterns):
        return CANDIDATE_PROFILE["projects"][2] # Platform Modernization
        
    # Default to flagship telemetry / backend / docker / python project
    return CANDIDATE_PROFILE["projects"][0] # Velocity Engine

def generate_quick_pitch(job_title: str, project_name: str, matched_skills: List[str]) -> str:
    skills_str = ", ".join(matched_skills[:3]) if matched_skills else "Python, REST APIs, and Docker"
    
    if "Velocity" in project_name:
        return f"Highlight your backend telemetry pipelines with {skills_str} and Dockerized microservices built in your Velocity Engine project to prove immediate engineering value as a {job_title}."
    elif "QA" in project_name or "E-Commerce" in project_name:
        return f"Emphasize your hands-on automated API test validation using {skills_str} and database integrity verification from your E-Commerce QA Suite to excel as a {job_title}."
    else:
        return f"Spotlight your experience modernizing user interfaces, authoring clean technical documentation, and delivering robust {skills_str} solutions to hit the ground running as a {job_title}."

def calculate_match_score(title: str, level: str, matched_skills: List[str]) -> int:
    score = 65 # Base score for relevant tech roles
    
    title_lower = title.lower()
    # Relevant keywords in title
    target_titles = ["software", "developer", "engineer", "qa", "python", "backend", "full stack", "cloud", "telemetry", "junior", "associate"]
    for t in target_titles:
        if t in title_lower:
            score += 5
            
    # Skill overlap bonus
    score += min(len(matched_skills) * 4, 20)
    
    # Seniority weighting
    if "Senior" in level or "Lead" in level:
        score -= 15
    elif "Fresh Grad" in level or "Junior" in level or "Entry" in level:
        score += 8
        
    return max(50, min(score, 95))

def generate_gemini_pitch(job_title: str, company: str, description: str, matched_skills: List[str], project: Dict[str, Any]) -> str:
    """Optional call to Google Gemini API if user configured GEMINI_API_KEY"""
    if not GEMINI_API_KEY:
        return None
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        prompt = f"""
You are an expert career agent assisting Engr. Maquee Reinhart P. Visitacion (Computer Engineering graduate with skills in Python, Node.js, PostgreSQL, Docker, Telemetry, and QA).
Job Title: {job_title} at {company}
Matched Skills: {', '.join(matched_skills)}
Candidate Project to highlight: {project['name']} ({project['summary']})
Job Description excerpt: {description[:1000]}

Write a concise, compelling 1-2 sentence "Quick Pitch" starting with "Highlight..." or "Spotlight..." explaining exactly how Maquee's project and skills demonstrate immediate value for this specific role. Output only the quotation-wrapped pitch.
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            pitch = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            pitch = pitch.strip('"').strip("'")
            return pitch
    except Exception as e:
        logger.warning(f"Gemini API pitch generation fallback: {e}")
    return None

def analyze_job(job: Dict[str, Any]) -> Any:
    """
    Analyzes a raw job listing from LinkedIn or Indeed and returns the structured evaluation
    matching the format in the user's friend's screenshot.
    Returns None if the job is NOT entry-level or junior friendly.
    """
    title = job.get("title", "Software Engineer").strip()
    company = job.get("company", "Company").strip()
    location = job.get("location", "Philippines").strip()
    source = job.get("site", "Linkedin").capitalize()
    date_posted = job.get("date_posted", "Recent")
    description = job.get("description", "") or ""
    
    # STRICT FILTER: Eliminate every non-junior / non-entry level position
    if not is_junior_or_entry_level(title, description):
        logger.info(f"Filtered out non-junior role: '{title}' at {company}")
        return None

    # STRICT AGE FILTER: Eliminate postings older than 3 months (~90 days)
    if not is_recent_post(date_posted, max_days=90):
        logger.info(f"Filtered out stale posting (>3 months old): '{title}' posted '{date_posted}'")
        return None
    
    # 1. Experience Level
    level = determine_experience_level(title, description)
    
    # 2. Stack Match
    full_text = f"{title} {description}"
    matched_skills = extract_stack_matches(full_text)
    if not matched_skills:
        matched_skills = ["Python", "REST APIs", "Git", "SQL"]
        
    # 3. Match Score
    match_score = calculate_match_score(title, level, matched_skills)
    
    # 4. Highlight Project
    project = select_highlight_project(title, matched_skills, description)
    
    # 5. Quick Pitch
    pitch = generate_gemini_pitch(title, company, description, matched_skills, project)
    if not pitch:
        pitch = generate_quick_pitch(title, project["name"], matched_skills)
        
    # Color badge
    if match_score >= 80:
        badge = "🟢"
    elif match_score >= 70:
        badge = "🟡"
    else:
        badge = "🔵"
        
    return {
        "title": title,
        "company": company,
        "location": location,
        "source": source,
        "date_posted": str(date_posted),
        "level": level,
        "badge": badge,
        "match_score": match_score,
        "stack_match": ", ".join(matched_skills),
        "highlight_project": project["name"],
        "quick_pitch": pitch,
        "job_url": job.get("job_url", "")
    }
