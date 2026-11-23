from unittest.mock import patch
from api.tasks.scraping_tasks import async_scrape_and_match

def test_scan_async_endpoint(client):
    """Test enqueuing an asynchronous job scan via FastAPI"""
    payload = {
        "role": "Junior Python Developer",
        "location": "Makati",
        "notify_telegram": False
    }

    mock_raw_jobs = [
        {
            "id": "async_job_1",
            "title": "Junior Python Developer",
            "company": "FastAPI Solutions",
            "location": "Makati",
            "site": "glassdoor",
            "job_url": "https://example.com/async-job",
            "date_posted": "Today",
            "description": "Python, Docker, SQL junior role."
        }
    ]

    with patch("api.tasks.scraping_tasks.fetch_jobs", return_value=mock_raw_jobs):
        res = client.post("/api/v1/jobs/scan-async", params=payload)
        assert res.status_code == 200
        data = res.json()
        assert "task_id" in data
        assert data["status"] == "QUEUED"
        assert f"/api/v1/tasks/{data['task_id']}" in data["poll_url"]

        # Check status endpoint
        task_res = client.get(data["poll_url"])
        assert task_res.status_code == 200
        task_data = task_res.json()
        assert task_data["task_id"] == data["task_id"]
        assert task_data["state"] in ["SUCCESS", "PENDING", "PROGRESS"]

def test_celery_task_execution(db_session):
    """Test execution of async_scrape_and_match task logic"""
    mock_raw_jobs = [
        {
            "id": "eager_job_99",
            "title": "Junior Software Engineer",
            "company": "Celery Corp",
            "location": "Taguig",
            "site": "linkedin",
            "job_url": "https://example.com/eager-job",
            "date_posted": "Yesterday",
            "description": "Entry level Python, REST APIs, Git."
        }
    ]

    with patch("api.tasks.scraping_tasks.fetch_jobs", return_value=mock_raw_jobs):
        async_res = async_scrape_and_match.apply(kwargs={
            "user_id": None,
            "role": "Junior Software Engineer",
            "location": "Taguig",
            "notify_telegram": False
        })

        assert async_res.successful()
        result = async_res.result
        assert result["status"] == "SUCCESS"
        assert result["total_scraped"] == 1
        assert result["matches_count"] == 1
        assert result["top_matches"][0]["company"] == "Celery Corp"
