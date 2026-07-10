import argparse
import csv
import json
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from parser import extract_job_detail, extract_jobs


TARGET_URL = "https://www.jobhai.com/jobs-in-jaipur-cty"
API_BASE_URL = "https://api.jobhai.com"
WEB_BASE_URL = "https://www.jobhai.com"
LIMIT = 10
BROWSER = "firefox"
MAX_PAGES = 5
JOB_ID_RE = re.compile(r"-(\d+)-jid(?:$|[?#])")
CSV_COLUMNS = [
    "job_title",
    "company",
    "location",
    "salary",
    "job_type",
    "experience",
    "posted",
    "job_description",
    "contact_person",
    "recruiter_phone",
    "recruiter_email",
    "job_url",
]


class ScraperError(RuntimeError):
    pass


def browser_context_options(storage_state=None):
    options = {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-IN",
        "timezone_id": "Asia/Kolkata",
        "extra_http_headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
        },
    }

    if storage_state:
        options["storage_state"] = storage_state

    return options


def launch_browser(playwright, browser_name=BROWSER, headless=True):
    if browser_name not in {"chromium", "firefox", "webkit"}:
        raise ScraperError("Browser must be chromium, firefox, or webkit")

    return getattr(playwright, browser_name).launch(headless=headless)


def get_html(url, browser_name=BROWSER):
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, browser_name=browser_name, headless=True)
        context = browser.new_context(**browser_context_options())
        page = context.new_page()

        try:
            return page_html(page, url)
        finally:
            browser.close()


def page_html(page, url, retries=2):
    last_error = None

    for attempt in range(retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("load", timeout=15000)
            except PlaywrightTimeoutError:
                pass
            return page.content()
        except PlaywrightError as exc:
            last_error = exc
            if attempt < retries:
                page.wait_for_timeout(1000)

    raise last_error


def listing_page_url(url, page_number):
    if page_number <= 1:
        return url

    parsed = urlparse(url)
    path = parsed.path
    if path.endswith("-cty"):
        if "-page-" in path:
            path = re.sub(r"-page-\d+-cty$", f"-page-{page_number}-cty", path)
        else:
            path = f"{path[:-4]}-page-{page_number}-cty"
        return urlunparse(parsed._replace(path=path))

    query = dict(parse_qsl(parsed.query))
    query["page"] = str(page_number)
    return urlunparse(parsed._replace(query=urlencode(query)))


def default_detail():
    return {
        "jobDescription": "",
        "contactPerson": "Not available",
        "recruiterPhone": "Not available",
        "recruiterEmail": "Not available",
    }


def load_storage_state(storage_state):
    if not storage_state:
        return None

    if isinstance(storage_state, dict):
        return storage_state

    return json.loads(Path(storage_state).read_text(encoding="utf-8"))


def auth_cookies_from_storage_state(storage_state):
    data = load_storage_state(storage_state)
    if not data:
        return {}

    return {cookie["name"]: cookie["value"] for cookie in data.get("cookies", [])}


def job_id_from_url(url):
    match = JOB_ID_RE.search(url or "")
    return match.group(1) if match else ""


def format_indian_phone(number):
    digits = re.sub(r"\D", "", str(number or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    if len(digits) == 10 and digits[0] in "6789":
        return f"+91 {digits}"

    return "Not available"


def contact_headers(cookies):
    access_token = cookies.get("access_token")
    device_id = cookies.get("deviceId", "")
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Language": "en",
        "source": "WEB",
        "device-source": "Desktop",
        "device-id": device_id,
        "deviceId": device_id,
        "Origin": WEB_BASE_URL,
        "Referer": f"{WEB_BASE_URL}/",
        "x-transaction-id": f"JS-WEB-{uuid.uuid4()}",
    }
    if access_token:
        headers["Authorization"] = access_token

    return headers


def contact_session(cookies):
    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".jobhai.com", path="/")

    return session


def get_recruiter_phone_via_call_api(job_id, storage_state):
    cookies = auth_cookies_from_storage_state(storage_state)
    if not cookies.get("access_token"):
        raise ScraperError("--include-recruiter-contact requires a logged-in auth state")

    session = contact_session(cookies)
    call_response = session.post(
        f"{API_BASE_URL}/jobs/v3/call",
        headers=contact_headers(cookies),
        json={"job_id": job_id},
        timeout=30,
    )
    call_response.raise_for_status()
    call_data = (call_response.json().get("data") or {})

    # Match the frontend behavior: only decrypt the contact when JobHai says
    # the call action is currently allowed.
    if not call_data.get("call_allowed"):
        return "Not available"

    encrypted_contact = call_data.get("job_contact")
    if not encrypted_contact:
        return "Not available"

    decrypt_response = session.post(
        f"{WEB_BASE_URL}/v1/utils/getInfo",
        headers=contact_headers(cookies),
        json={"number": encrypted_contact},
        timeout=30,
    )
    decrypt_response.raise_for_status()
    number = (decrypt_response.json().get("data") or {}).get("number")

    return format_indian_phone(number)


def add_recruiter_contacts(jobs, storage_state):
    for job in jobs:
        job_id = job_id_from_url(job.get("link", ""))
        if not job_id:
            continue

        try:
            phone = get_recruiter_phone_via_call_api(job_id, storage_state)
        except requests.RequestException:
            phone = "Not available"

        if phone != "Not available":
            job["recruiterPhone"] = phone

    return jobs


def scrape_jobs_from_html_loader(
    url=TARGET_URL,
    limit=LIMIT,
    html_loader=get_html,
    include_details=True,
    full_time_only=True,
    max_pages=MAX_PAGES,
):
    jobs = []
    seen_links = set()

    try:
        for page_number in range(1, max_pages + 1):
            page_url = listing_page_url(url, page_number)
            html = html_loader(page_url)
            page_jobs = extract_jobs(
                html,
                base_url=page_url,
                limit=limit,
                full_time_only=full_time_only,
            )

            for job in page_jobs:
                key = job.get("link") or "|".join(
                    [job.get("title", ""), job.get("company", "")]
                )
                if key in seen_links:
                    continue

                seen_links.add(key)
                jobs.append(job)
                if len(jobs) >= limit:
                    break

            if len(jobs) >= limit or not page_jobs:
                break
    except PlaywrightTimeoutError as exc:
        raise ScraperError("Scraper timed out while loading JobHai") from exc
    except PlaywrightError as exc:
        raise ScraperError(str(exc)) from exc

    if not jobs:
        raise ScraperError("JobHai page did not expose job cards")

    if include_details:
        for job in jobs:
            detail = default_detail()
            if job.get("link"):
                detail.update(extract_job_detail(html_loader(job["link"])))
            job.update(detail)

    return jobs


def scrape_jobs(
    url=TARGET_URL,
    limit=LIMIT,
    html_loader=None,
    include_details=True,
    full_time_only=True,
    storage_state=None,
    headless=True,
    browser_name=BROWSER,
    max_pages=MAX_PAGES,
    include_recruiter_contact=False,
):
    if html_loader:
        return scrape_jobs_from_html_loader(
            url=url,
            limit=limit,
            html_loader=html_loader,
            include_details=include_details,
            full_time_only=full_time_only,
            max_pages=max_pages,
        )

    try:
        with sync_playwright() as playwright:
            browser = launch_browser(
                playwright,
                browser_name=browser_name,
                headless=headless,
            )
            context = browser.new_context(
                **browser_context_options(storage_state=storage_state)
            )
            page = context.new_page()

            try:
                jobs = []
                seen_links = set()
                for page_number in range(1, max_pages + 1):
                    page_url = listing_page_url(url, page_number)
                    html = page_html(page, page_url)
                    page_jobs = extract_jobs(
                        html,
                        base_url=page_url,
                        limit=limit,
                        full_time_only=full_time_only,
                    )

                    for job in page_jobs:
                        key = job.get("link") or "|".join(
                            [job.get("title", ""), job.get("company", "")]
                        )
                        if key in seen_links:
                            continue

                        seen_links.add(key)
                        jobs.append(job)
                        if len(jobs) >= limit:
                            break

                    if len(jobs) >= limit or not page_jobs:
                        break

                if not jobs:
                    raise ScraperError("JobHai page did not expose job cards")

                if include_details:
                    for job in jobs:
                        detail = default_detail()
                        if job.get("link"):
                            try:
                                detail.update(
                                    extract_job_detail(page_html(page, job["link"]))
                                )
                            except PlaywrightError:
                                detail["jobDescription"] = " ".join(
                                    job.get("details", [])
                                )
                        job.update(detail)

                if include_recruiter_contact:
                    add_recruiter_contacts(jobs, storage_state)

                return jobs
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise ScraperError("Scraper timed out while loading JobHai") from exc
    except PlaywrightError as exc:
        raise ScraperError(str(exc)) from exc


def job_to_csv_row(job):
    return {
        "job_title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "salary": job.get("salary", ""),
        "job_type": job.get("jobType", ""),
        "experience": job.get("experience", ""),
        "posted": job.get("posted", ""),
        "job_description": job.get("jobDescription", ""),
        "contact_person": job.get("contactPerson", "Not available"),
        "recruiter_phone": job.get("recruiterPhone", "Not available"),
        "recruiter_email": job.get("recruiterEmail", "Not available"),
        "job_url": job.get("link", ""),
    }


def write_csv(jobs, output_path):
    output = Path(output_path)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for job in jobs:
            writer.writerow(job_to_csv_row(job))

    return output


def save_login_state(path, url=TARGET_URL, browser_name=BROWSER):
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, browser_name=browser_name, headless=False)
        context = browser.new_context(**browser_context_options())
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        input("Log in to JobHai in the opened browser, then press Enter here: ")
        context.storage_state(path=path)
        browser.close()


def main():
    arg_parser = argparse.ArgumentParser(
        description="Scrape the latest JobHai Jaipur jobs and save a CSV."
    )
    arg_parser.add_argument("--url", default=TARGET_URL, help="JobHai listing URL")
    arg_parser.add_argument("--limit", type=int, default=LIMIT, help="Number of jobs")
    arg_parser.add_argument(
        "--output",
        default="jobhai_jaipur_jobs.csv",
        help="CSV file path",
    )
    arg_parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES,
        help="Maximum listing pages to scan",
    )
    arg_parser.add_argument(
        "--all-job-types",
        action="store_true",
        help="Do not filter to full-time jobs",
    )
    arg_parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip opening detail pages",
    )
    arg_parser.add_argument(
        "--auth-state",
        default=None,
        help="Optional Playwright storage state JSON from --login",
    )
    arg_parser.add_argument(
        "--include-recruiter-contact",
        action="store_true",
        help=(
            "Use the logged-in Call HR API to fetch recruiter phones when JobHai "
            "allows calling. Requires --auth-state and may send applications."
        ),
    )
    arg_parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default=BROWSER,
        help="Playwright browser backend",
    )
    arg_parser.add_argument(
        "--login",
        action="store_true",
        help="Open a browser to log in and save --auth-state",
    )
    arg_parser.add_argument(
        "--print-json",
        action="store_true",
        help="Also print scraped jobs as JSON",
    )
    args = arg_parser.parse_args()

    if args.login:
        save_login_state(
            args.auth_state or "jobhai_auth.json",
            url=args.url,
            browser_name=args.browser,
        )
        print(f"Saved login state to {args.auth_state or 'jobhai_auth.json'}")
        return 0

    try:
        jobs = scrape_jobs(
            url=args.url,
            limit=args.limit,
            include_details=not args.no_details,
            full_time_only=not args.all_job_types,
            storage_state=args.auth_state,
            browser_name=args.browser,
            max_pages=args.max_pages,
            include_recruiter_contact=args.include_recruiter_contact,
        )
    except ScraperError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output = write_csv(jobs, args.output)
    print(f"Saved {len(jobs)} jobs to {output}")

    if args.print_json:
        print(json.dumps(jobs, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
