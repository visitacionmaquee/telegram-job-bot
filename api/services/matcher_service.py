import re
from typing import Dict, Any, List
from resume_profile import CANDIDATE_PROFILE
from matcher import (
    is_junior_or_entry_level,
    is_recent_post,
    determine_experience_level,
    generate_recruiter_note
)

def extract_matched_skills(text: str, candidate_skills: List[str] = None) -> List[str]:
    """Extract overlapping skills between job description and candidate's skill list"""
    text_lower = text.lower()
    matches = []

    # Default common tech dictionary
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
        "fastapi": "FastAPI",
        "react": "React",
    }

    # Add any custom candidate skills dynamically
    if candidate_skills:
        for s in candidate_skills:
            clean = s.strip()
            if clean:
                skill_mapping[clean.lower()] = clean

    for needle, clean_name in skill_mapping.items():
        pattern = r'\b' + re.escape(needle) + r'\b'
        if re.search(pattern, text_lower):
            if clean_name not in matches:
                matches.append(clean_name)

    return matches

def select_project(job_title: str, matched_skills: List[str], description: str, candidate_projects: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dynamically matches the best project from candidate's profile"""
    projects = candidate_projects or CANDIDATE_PROFILE.get("projects", [])
    if not projects:
        return {"name": "Software Engineering Portfolio", "summary": "Full stack application development"}

    text = (job_title + " " + " ".join(matched_skills) + " " + (description or "")).lower()

    # Score each project by keyword overlap
    best_project = projects[0]
    best_score = -1

    for p in projects:
        score = 0
        keywords = p.get("best_fit_keywords", [])
        for kw in keywords:
            if kw.lower() in text:
                score += 2
        for tech in p.get("technologies", []):
            if tech.lower() in text:
                score += 1

        if score > best_score:
            best_score = score
            best_project = p

    return best_project

def calculate_score(title: str, level: str, matched_skills: List[str]) -> int:
    score = 65
    title_lower = title.lower()
    target_titles = ["software", "developer", "engineer", "qa", "python", "backend", "full stack", "cloud", "telemetry", "junior", "associate"]
    for t in target_titles:
        if t in title_lower:
            score += 5

    score += min(len(matched_skills) * 4, 20)

    if "Senior" in level or "Lead" in level:
        score -= 15
    elif "Fresh Grad" in level or "Junior" in level or "Entry" in level:
        score += 8

    return max(50, min(score, 95))

def evaluate_job_match(job_dict: Dict[str, Any], candidate_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Evaluates a job against a candidate profile.
    Returns matched details or None if filtered out (e.g. senior or stale).
    """
    title = job_dict.get("title", "Software Engineer").strip()
    company = job_dict.get("company", "Company").strip()
    location = job_dict.get("location", "Philippines").strip()
    source = job_dict.get("source", job_dict.get("site", "linkedin")).capitalize()
    date_posted = job_dict.get("date_posted", "Recent")
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
        # Flatten dictionary of skills if nested
        flat = []
        for v in skills_list.values():
            flat.extend(v if isinstance(v, list) else [v])
        skills_list = flat

    level = determine_experience_level(title, description)
    matched_skills = extract_matched_skills(f"{title} {description}", skills_list)
    if not matched_skills:
        matched_skills = ["Python", "REST APIs", "Git", "SQL"]

    match_score = calculate_score(title, level, matched_skills)

    project = select_project(title, matched_skills, description, profile.get("projects", []))
    project_name = project.get("name", "Engineering Portfolio")

    # Generate custom pitch
    skills_str = ", ".join(matched_skills[:3])
    pitch = f"Highlight your engineering experience with {skills_str} and key contributions in {project_name.split('—')[0].strip()} to prove immediate technical value as a {title}."

    # Generate recruiter notes
    notes = generate_recruiter_note(
        job_title=title,
        company=company,
        highlight_project=project_name,
        stack_match=", ".join(matched_skills)
    )

    badge = "🟢" if match_score >= 80 else ("🟡" if match_score >= 70 else "🔵")

    return {
        "job_id": job_dict.get("id"),
        "title": title,
        "company": company,
        "location": location,
        "source": source,
        "url": job_dict.get("url", job_dict.get("job_url", "")),
        "date_posted": str(date_posted),
        "level": level,
        "badge": badge,
        "match_score": match_score,
        "stack_match": ", ".join(matched_skills),
        "highlight_project": project_name,
        "quick_pitch": pitch,
        "outreach_linkedin": notes.get("linkedin_note"),
        "outreach_email": notes.get("email_note")
    }
