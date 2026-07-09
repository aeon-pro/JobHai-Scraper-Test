from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scraper.extract import extract_jobs
from test import get_html as default_get_html


TARGET_URL = "https://www.jobhai.com/jobs-in-jaipur-cty"
LIMIT = 10


class ScraperError(RuntimeError):
    pass


def scrape_jobs(url=TARGET_URL, limit=LIMIT, get_html=default_get_html):
    try:
        html = get_html(url)
    except PlaywrightTimeoutError as exc:
        raise ScraperError("Scraper timed out while loading JobHai") from exc
    except PlaywrightError as exc:
        raise ScraperError(str(exc)) from exc

    jobs = extract_jobs(html, base_url=url, limit=limit)
    if not jobs:
        raise ScraperError("JobHai page did not expose job cards")

    return jobs
