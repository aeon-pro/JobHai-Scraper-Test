import pytest


def test_home_page_renders_load_workflow():
    import webapp as app_module

    app_module.app.config.update(TESTING=True)
    client = app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "JobHai Jaipur Job Scraper" in body
    assert "Load Jobs" in body
    assert "/api/jobs" in body


def test_jobs_endpoint_returns_scraped_jobs(monkeypatch):
    import webapp as app_module

    sample_jobs = [
        {
            "title": "Telecaller",
            "company": "Acme Hiring",
            "location": "Mansarovar, Jaipur",
            "salary": "Rs 18,000 - Rs 25,000 per month",
            "jobType": "Full Time",
            "experience": "0 - 2 years",
            "posted": "Posted 1 day ago",
            "link": "https://www.jobhai.com/job/telecaller-1",
            "details": [
                "Full Time",
                "0 - 2 years",
                "Rs 18,000 - Rs 25,000 per month",
                "Mansarovar, Jaipur",
                "Posted 1 day ago",
            ],
        }
    ]
    monkeypatch.setattr(app_module, "run_scraper", lambda: sample_jobs)
    app_module.app.config.update(TESTING=True)
    client = app_module.app.test_client()

    response = client.get("/api/jobs")

    assert response.status_code == 200
    assert response.get_json() == {"count": 1, "jobs": sample_jobs}


def test_jobs_endpoint_reports_scraper_errors(monkeypatch):
    import webapp as app_module

    def broken_scraper():
        raise app_module.ScraperError("JobHai page did not expose job cards")

    monkeypatch.setattr(app_module, "run_scraper", broken_scraper)
    app_module.app.config.update(TESTING=True)
    client = app_module.app.test_client()

    response = client.get("/api/jobs")

    assert response.status_code == 502
    assert response.get_json() == {
        "error": "JobHai page did not expose job cards",
    }
