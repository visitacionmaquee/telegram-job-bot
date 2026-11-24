import re
from typing import Dict, Any, List, Tuple, Optional
from resume_profile import CANDIDATE_PROFILE
from matcher import (
    is_junior_or_entry_level,
    is_recent_post,
    determine_experience_level,
    generate_recruiter_note
)

def clean_location(loc: str) -> str:
    """Sanitizes location strings by stripping Indeed administrative region codes (P00, 00)"""
    if not loc:
        return "Philippines"
    cleaned = re.sub(r'\b(P00|00|PH-00|PH-P00)\b', '', loc, flags=re.IGNORECASE)
    cleaned = re.sub(r',\s*,+', ',', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,')
    return cleaned or "Philippines"

def detect_work_setup(title: str, description: str, location: str) -> str:
    """Classifies position work arrangement as Remote, Hybrid, or On-site"""
    combined = f"{title} {description} {location}".lower()
    if any(k in combined for k in ["remote", "work from home", "wfh", "anywhere in ph", "virtual"]):
        return "Remote"
    elif any(k in combined for k in ["hybrid", "days onsite", "days in office", "flexible"]):
        return "Hybrid"
    return "On-site"

def detect_salary(text: str) -> Optional[str]:
    """Extracts salary range if explicitly stated in text"""
    patterns = [
        r'(?:₱|php|php\.)\s*[\d,]+(?:\s*-\s*(?:₱|php|php\.)?\s*[\d,]+)?(?:\s*(?:per month|\/mo|monthly|\/yr|annually))?',
        r'\$\s*[\d,]+(?:\s*-\s*\$?\s*[\d,]+)?(?:\s*(?:per month|\/mo|monthly|\/yr|annually))?'
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            clean = match.group(0).strip()
            if len(clean) > 3:
                return clean
    return None

# Comprehensive tech dictionary for both candidate match and gap detection
TECH_CATALOG = {
    # Backend & General
    "python": "Python", "node": "Node.js", "node.js": "Node.js", "fastapi": "FastAPI",
    "flask": "Flask", "django": "Django", "express": "Express.js",
    "sql": "SQL", "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "docker": "Docker", "linux": "Linux", "bash": "Bash", "git": "Git",
    "rest": "REST APIs", "restful": "REST APIs", "api": "REST APIs", "microservices": "Microservices",
    "postman": "Postman", "selenium": "Selenium", "qa": "QA Testing", "testing": "QA Testing",
    "prometheus": "Prometheus", "grafana": "Grafana", "telemetry": "Telemetry",
    "oracle cloud": "Oracle Cloud", "cloud": "Cloud Computing", "ci/cd": "CI/CD",
    "javascript": "JavaScript", "typescript": "TypeScript",

    # Common Gap Stacks
    "unity": "Unity", "unreal": "Unreal Engine", "godot": "Godot", "game dev": "Game Development",
    "c#": "C#", "c++": "C++", ".net": ".NET", "asp.net": "ASP.NET",
    "flutter": "Flutter", "react native": "React Native", "swift": "Swift", "kotlin": "Kotlin",
    "ios": "iOS", "android": "Android",
    "aws": "AWS", "azure": "Azure", "gcp": "GCP", "kubernetes": "Kubernetes",
    "react": "React", "angular": "Angular", "vue": "Vue.js", "next.js": "Next.js",
    "salesforce": "Salesforce", "sap": "SAP", "php": "PHP", "laravel": "Laravel", "ruby": "Ruby"
}

def extract_skills_and_gaps(text: str, candidate_skills: List[str] = None) -> Tuple[List[str], List[str]]:
    """
    Extracts overlapping skills (matched) and required job technologies lacking in candidate profile (missing).
    """
    text_lower = text.lower()
    candidate_skills_lower = set(s.lower() for s in (candidate_skills or []))

    # Add candidate default skills if none provided
    if not candidate_skills_lower:
        default_skills = CANDIDATE_PROFILE.get("skills", {})
        if isinstance(default_skills, dict):
            for v in default_skills.values():
                candidate_skills_lower.update(s.lower() for s in v)

    matched = []
    missing = []

    for needle, clean_name in TECH_CATALOG.items():
        pattern = r'\b' + re.escape(needle) + r'\b'
        if re.search(pattern, text_lower):
            # Check if candidate has this skill
            is_matched = any(needle in cs or cs in needle for cs in candidate_skills_lower)
            if is_matched:
                if clean_name not in matched:
                    matched.append(clean_name)
            else:
                if clean_name not in missing and clean_name not in matched:
                    missing.append(clean_name)

    return matched, missing

def select_project(job_title: str, matched_skills: List[str], description: str, candidate_projects: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dynamically matches the best project from candidate's profile"""
    projects = candidate_projects or CANDIDATE_PROFILE.get("projects", [])
    if not projects:
        return {"name": "Software Engineering Portfolio", "summary": "Full stack application development"}

    text = (job_title + " " + " ".join(matched_skills) + " " + (description or "")).lower()

    best_project = projects[0]
    best_score = -1

    for p in projects:
        score = 0
        keywords = p.get("best_fit_keywords", [])
        for kw in keywords:
            if kw.lower() in text:
                score += 3
        for tech in p.get("technologies", []):
            if tech.lower() in text:
                score += 2

        if score > best_score:
            best_score = score
            best_project = p

    return best_project

def calculate_score(
    title: str,
    level: str,
    matched_skills: List[str],
    missing_skills: List[str],
    target_roles: List[str] = None
) -> int:
    """
    Calibrated match scorer:
    Distributes scores realistically between 50% and 94% based on title relevance,
    skills overlap ratio, and domain penalties (e.g. Game Dev when candidate lacks game stack).
    """
    title_lower = title.lower()

    # Base score
    score = 55

    # 1. Target Role Alignment (+10 to +20)
    roles = [r.lower() for r in (target_roles or [
        "junior software engineer", "entry level software engineer",
        "junior developer", "junior python developer", "junior qa engineer"
    ])]

    if any(r in title_lower for r in roles):
        score += 15
    elif any(k in title_lower for k in ["software", "developer", "engineer", "qa", "python", "backend", "full stack"]):
        score += 10

    # 2. Level adjustment
    if "Fresh Grad" in level or "Entry" in level or "Junior" in level or "Associate" in level:
        score += 8
    elif "Mid" in level:
        score += 2
    elif "Senior" in level or "Lead" in level:
        score -= 20

    # 3. Matched Skills Gain (+3 per skill, max 15)
    score += min(len(matched_skills) * 3, 15)

    # 4. Missing Skills Penalty (-3 per gap skill, max 15)
    score -= min(len(missing_skills) * 3, 15)

    # 5. Specialized Domain Mismatch Penalty (-25%)
    # If job specifically targets a domain where candidate has zero matching skills:
    specialized_domains = {
        "game": ["Unity", "Unreal Engine", "Godot", "Game Development", "C++", "C#"],
        "gaming": ["Unity", "Unreal Engine", "Godot", "Game Development", "C++", "C#"],
        "ios": ["Swift", "iOS"],
        "android": ["Kotlin", "Android"],
        "flutter": ["Flutter"],
        "salesforce": ["Salesforce"],
        "sap": ["SAP"],
        "embedded": ["C", "C++", "Microcontroller"]
    }

    for domain_kw, req_skills in specialized_domains.items():
        if domain_kw in title_lower:
            domain_matched = any(s in matched_skills for s in req_skills)
            if not domain_matched:
                score -= 25 # Strong penalty for unrelated domain

    return max(48, min(score, 94))

def evaluate_job_match(job_dict: Dict[str, Any], candidate_profile: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Evaluates a job against a candidate profile.
    Returns matched details or None if filtered out (e.g. senior or stale).
    """
    title = job_dict.get("title", "Software Engineer").strip()
    company = job_dict.get("company", "Company").strip()
    raw_location = job_dict.get("location", "Philippines").strip()
    location = clean_location(raw_location)
    source = job_dict.get("source", job_dict.get("site", "linkedin")).capitalize()
    date_posted = str(job_dict.get("date_posted", "Recent"))
    description = job_dict.get("description", "") or ""

    # Strict seniority filter
    if not is_junior_or_entry_level(title, description):
        return None

    # Strict date freshness filter (< 3 months)
    if not is_recent_post(date_posted, max_days=90):
        return None

    profile = candidate_profile or CANDIDATE_PROFILE
    skills_list = profile.get("skills", [])
    if isinstance(skills_list, dict):
        flat = []
        for v in skills_list.values():
            flat.extend(v if isinstance(v, list) else [v])
        skills_list = flat

    level = determine_experience_level(title, description)
    matched_skills, missing_skills = extract_skills_and_gaps(f"{title} {description}", skills_list)

    target_roles = profile.get("target_roles", [])
    match_score = calculate_score(title, level, matched_skills, missing_skills, target_roles)

    project = select_project(title, matched_skills, description, profile.get("projects", []))
    project_name = project.get("name", "Engineering Portfolio")

    work_setup = detect_work_setup(title, description, location)
    salary = detect_salary(f"{title} {description}")

    # Generate custom pitch
    top_skills_str = ", ".join(matched_skills[:3]) if matched_skills else "Python, REST APIs, Git"
    pitch = f"Highlight your hands-on engineering background in {top_skills_str} and key contributions in {project_name.split('—')[0].strip()} to prove immediate technical value for this {title} role."

    # Generate recruiter notes
    notes = generate_recruiter_note(
        job_title=title,
        company=company,
        highlight_project=project_name,
        stack_match=", ".join(matched_skills)
    )

    badge = "🟢" if match_score >= 82 else ("🟡" if match_score >= 70 else "🔵")

    return {
        "job_id": job_dict.get("id"),
        "title": title,
        "company": company,
        "location": location,
        "source": source,
        "url": job_dict.get("url", job_dict.get("job_url", "")),
        "date_posted": date_posted,
        "work_setup": work_setup,
        "salary": salary,
        "level": level,
        "badge": badge,
        "match_score": match_score,
        "matched_skills": matched_skills[:4],
        "missing_skills": missing_skills[:3],
        "stack_match": ", ".join(matched_skills),
        "highlight_project": project_name,
        "quick_pitch": pitch,
        "outreach_linkedin": notes.get("linkedin_note"),
        "outreach_email": notes.get("email_note")
    }

# Backward compatibility alias
def extract_matched_skills(text: str, candidate_skills: List[str] = None) -> List[str]:
    matched, _ = extract_skills_and_gaps(text, candidate_skills)
    return matched
