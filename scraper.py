import argparse
import json
import sys

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from parser import extract_jobs


TARGET_URL = "https://www.jobhai.com/jobs-in-jaipur-cty"
LIMIT = 10


class ScraperError(RuntimeError):
    pass


def get_html(url):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-IN,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("load", timeout=60000)
            return page.content()
        finally:
            browser.close()


def scrape_jobs(url=TARGET_URL, limit=LIMIT, get_html=get_html):
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


def main():
    arg_parser = argparse.ArgumentParser(
        description="Scrape the top JobHai Jaipur jobs and print JSON."
    )
    arg_parser.add_argument("--url", default=TARGET_URL, help="JobHai listing URL")
    arg_parser.add_argument("--limit", type=int, default=LIMIT, help="Number of jobs")
    args = arg_parser.parse_args()

    try:
        jobs = scrape_jobs(url=args.url, limit=args.limit)
    except ScraperError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(jobs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
