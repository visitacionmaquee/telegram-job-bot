import pytest
from api import models

def test_dashboard_endpoint(client):
    """Verify that the dashboard HTML UI is served correctly at /dashboard"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "JobRadar AI" in response.text
    assert "Kanban" in response.text

def test_default_user_auto_provisioning(client, db_session):
    """Verify GET /api/v1/users/default automatically provisions candidate profile"""
    response = client.get("/api/v1/users/default")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert data["email"] == "visitacionmaquee@gmail.com"
    assert "Engr. Maquee" in data["full_name"]
    assert data["telegram_chat_id"] == "8880104517"
    assert data["profile"] is not None
    assert "Python" in data["profile"]["skills"]

def test_dashboard_pipeline_kanban_flow(client, db_session):
    """Verify application creation, stage movement, and pipeline stats calculation"""
    # 1. Fetch default user
    user_res = client.get("/api/v1/users/default")
    user_id = user_res.json()["id"]

    # 2. Create mock job
    job = models.Job(
        id="dash_test_job_1",
        title="Junior Cloud Systems Engineer",
        company="TechCorp Global",
        location="Manila, Philippines",
        source="linkedin",
        url="https://linkedin.com/jobs/view/12345",
        date_posted="1 day ago"
    )
    db_session.add(job)
    db_session.commit()

    # 3. Add to Kanban (saved)
    create_res = client.post(
        f"/api/v1/applications?user_id={user_id}",
        json={
            "job_id": "dash_test_job_1",
            "status": "saved",
            "match_score": 92,
            "highlight_project": "Velocity Engine — Hardware Telemetry & Observability Platform",
            "quick_pitch": "Leverage Docker and Python microservices experience."
        }
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["id"]
    assert create_res.json()["status"] == "saved"
    assert create_res.json()["job"]["title"] == "Junior Cloud Systems Engineer"

    # 4. Move to applied
    patch_res = client.patch(
        f"/api/v1/applications/{app_id}",
        json={"status": "applied", "notes": "Applied via LinkedIn Easy Apply"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "applied"

    # 5. Check stats reflect the change
    stats_res = client.get(f"/api/v1/applications/pipeline-stats?user_id={user_id}")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["applied"] >= 1
    assert stats["total"] >= 1
