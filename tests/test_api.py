def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_user_creation_and_profile(client):
    # 1. Create User
    payload = {
        "email": "maquee@example.com",
        "full_name": "Engr. Maquee Reinhart Visitacion",
        "telegram_chat_id": "8880104517",
        "tier": "pro"
    }
    res = client.post("/api/v1/users", json=payload)
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == "maquee@example.com"
    user_id = user_data["id"]

    # 2. Duplicate user check
    res_dup = client.post("/api/v1/users", json=payload)
    assert res_dup.status_code == 400

    # 3. Get user
    res_get = client.get(f"/api/v1/users/{user_id}")
    assert res_get.status_code == 200
    assert res_get.json()["full_name"] == "Engr. Maquee Reinhart Visitacion"

    # 4. Update Profile
    profile_payload = {
        "headline": "Computer Engineering Graduate & Full Stack Developer",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Prometheus"],
        "target_roles": ["Junior Software Engineer", "Backend Developer"],
        "min_match_percent": 75
    }
    res_profile = client.put(f"/api/v1/users/{user_id}/profile", json=profile_payload)
    assert res_profile.status_code == 200
    pdata = res_profile.json()
    assert "FastAPI" in pdata["skills"]
    assert pdata["min_match_percent"] == 75

def test_application_kanban_flow(client, db_session):
    from api import models

    # Create user
    user = models.User(email="test@user.com", full_name="Test User")
    db_session.add(user)
    db_session.commit()

    # Create job
    job = models.Job(
        id="job_hash_123",
        title="Junior Python Developer",
        company="Tech Corp",
        location="Makati",
        source="linkedin",
        url="https://example.com/job/123"
    )
    db_session.add(job)
    db_session.commit()

    # 1. Add application to Kanban (saved column)
    app_payload = {
        "job_id": "job_hash_123",
        "status": "saved",
        "match_score": 88,
        "highlight_project": "Velocity Engine",
        "quick_pitch": "Highlight backend pipelines in Python"
    }
    res = client.post(f"/api/v1/applications?user_id={user.id}", json=app_payload)
    assert res.status_code == 201
    app_id = res.json()["id"]

    # 2. Check pipeline stats (Saved: 1)
    res_stats = client.get(f"/api/v1/applications/pipeline-stats?user_id={user.id}")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["saved"] == 1
    assert stats["applied"] == 0

    # 3. Move card to "applied"
    res_update = client.patch(f"/api/v1/applications/{app_id}", json={"status": "applied"})
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "applied"

    # 4. Verify pipeline stats updated
    res_stats2 = client.get(f"/api/v1/applications/pipeline-stats?user_id={user.id}")
    assert res_stats2.json()["applied"] == 1
    assert res_stats2.json()["saved"] == 0
