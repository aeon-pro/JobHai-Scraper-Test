from pathlib import Path

from scraper import TARGET_URL, scrape_jobs


FIXTURE = Path(__file__).parent / "fixtures" / "jobhai-jaipur.html"


def test_scrape_jobs_gets_html_then_extracts_top_ten_jobs():
    calls = []

    def fake_get_html(url):
        calls.append(url)
        return FIXTURE.read_text()

    jobs = scrape_jobs(get_html=fake_get_html)

    assert calls == [TARGET_URL]
    assert len(jobs) == 10
    assert jobs[0]["title"] == "Telecaller"
