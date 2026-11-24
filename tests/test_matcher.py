from api.services.matcher_service import (
    extract_matched_skills,
    select_project,
    evaluate_job_match
)

def test_extract_matched_skills():
    text = "We are seeking a Junior Developer with strong Python, Docker, PostgreSQL, and REST API skills."
    skills = extract_matched_skills(text)
    assert "Python" in skills
    assert "Docker" in skills
    assert "PostgreSQL" in skills
    assert "REST APIs" in skills

def test_select_project_telemetry():
    job_title = "Backend Observability Engineer"
    matched_skills = ["Python", "Prometheus", "Grafana", "Docker"]
    desc = "Experience with metrics logging, telemetry streaming, and containerized services."
    project = select_project(job_title, matched_skills, desc)
    assert "Velocity" in project["name"]

def test_select_project_qa():
    job_title = "Junior QA Tester"
    matched_skills = ["Postman", "Selenium", "QA Testing"]
    desc = "Automated test suites, API verification, and bug reports."
    project = select_project(job_title, matched_skills, desc)
    assert "QA" in project["name"] or "E-Commerce" in project["name"]

def test_evaluate_job_match_senior_rejection():
    job = {
        "id": "senior_123",
        "title": "Senior Principal Software Architect",
        "company": "Enterprise Corp",
        "location": "Makati",
        "date_posted": "2 days ago",
        "description": "Requires at least 10 years of experience leading engineering teams."
    }
    evaluated = evaluate_job_match(job)
    # Must be filtered out because user is fresh grad
    assert evaluated is None

def test_evaluate_job_match_entry_level_success():
    job = {
        "id": "junior_123",
        "title": "Junior Python Developer",
        "company": "Inspiro Tech",
        "location": "Pasig, Philippines",
        "date_posted": "Yesterday",
        "url": "https://example.com/junior-dev",
        "description": "Looking for fresh graduates with foundational knowledge in Python, SQL, and Docker."
    }
    evaluated = evaluate_job_match(job)
    assert evaluated is not None
    assert evaluated["match_score"] >= 70
    assert evaluated["badge"] in ["🟢", "🟡"]
    assert "Velocity" in evaluated["highlight_project"] or "Engineering" in evaluated["highlight_project"]
    assert len(evaluated["outreach_linkedin"]) <= 300 # Fits LinkedIn limit

def test_clean_location_removes_p00():
    from api.services.matcher_service import clean_location
    assert clean_location("Quezon City, P00, Philippines") == "Quezon City, Philippines"
    assert clean_location("Taguig, P00, Philippines") == "Taguig, Philippines"
    assert clean_location("P00, Philippines") == "Philippines"

def test_game_developer_gap_penalization():
    job = {
        "id": "game_1",
        "title": "Junior Game Developer",
        "company": "Gaming Studio",
        "location": "Quezon City, P00, Philippines",
        "date_posted": "Recent",
        "description": "Looking for Unity, C#, 3D Game Physics developers."
    }
    evaluated = evaluate_job_match(job)
    assert evaluated is not None
    assert evaluated["match_score"] < 65
    assert "Unity" in evaluated["missing_skills"]
    assert "P00" not in evaluated["location"]

def test_detect_work_setup():
    from api.services.matcher_service import detect_work_setup
    assert detect_work_setup("Software Engineer", "Full remote work from home", "Manila") == "Remote"
    assert detect_work_setup("QA Engineer", "Hybrid work setup 2 days office", "Taguig") == "Hybrid"
    assert detect_work_setup("Backend Developer", "Office based daily", "Makati") == "On-site"
