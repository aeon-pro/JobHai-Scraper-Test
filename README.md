# JobHai Jaipur Job Scraper

A small Python project that scrapes the latest JobHai listings for Jaipur,
opens each job detail page, and saves clean structured results to CSV.

## Files

- `parser.py` parses JobHai listing and detail HTML into structured job records.
- `scraper.py` loads JobHai with Playwright and saves jobs to CSV.
- `webapp.py` serves a Flask page with a **Load Jobs** button.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install firefox
```

Firefox is the recommended Playwright backend for JobHai. In local testing,
Chromium/Chrome returned HTTP/2 protocol errors while Firefox-based Zen loaded
the site normally.

## Run the assignment scraper

```bash
python3 scraper.py
```

This creates:

```text
jobhai_jaipur_jobs.csv
```

The CSV columns are:

```text
job_title, company, location, salary, job_type, experience, posted,
job_description, contact_person, recruiter_phone, recruiter_email, job_url
```

Useful options:

```bash
python3 scraper.py --limit 5
python3 scraper.py --output jaipur_jobs.csv
python3 scraper.py --print-json
```

By default, the script filters to full-time jobs and opens detail pages for
the full job description.

If you intentionally want to copy or trim an existing CSV instead of scraping
fresh JobHai data, use:

```bash
python3 scraper.py --from-csv jobhai_jaipur_jobs.csv --output jobhai_jaipur_jobs.csv
```

Normal scraper runs do not reuse old CSV data. If JobHai blocks or resets the
live page, the command exits with an error so you know fresh data was not saved.

## Login state

Recommended terminal OTP login:

```bash
python3 scraper.py --otp-login YOUR_PHONE_NUMBER --auth-state jobhai_auth.json
```

Enter the OTP when prompted. This creates a local `jobhai_auth.json` file with
JobHai cookies, including `access_token`, `access_id`, and `deviceId`.

Alternative browser login:

```bash
python3 scraper.py --login --auth-state jobhai_auth.json
```

Complete login in the opened browser, then press Enter in the terminal.

You can confirm the auth file exists:

```bash
ls jobhai_auth.json
```

Then use it in future scraper runs:

```bash
python3 scraper.py --auth-state jobhai_auth.json
```

The auth state is used only for logged-in recruiter contact API calls. Listing
and detail pages are scraped in public mode because the logged-in page can render
a different shell that does not expose the same job cards.

Do not commit or upload `jobhai_auth.json`. It contains private login tokens
for the JobHai account. The file is already listed in `.gitignore`.

Recruiter phone/email are saved only when they are visible in the page text.
If JobHai does not expose them, the CSV stores `Not available`.

## Recruiter phone numbers

JobHai does not expose recruiter phone numbers in the public HTML. In the
logged-in website, the **Call HR** button calls `jobs/v3/call`, then decrypts
the returned contact token through `www.jobhai.com/v1/utils/getInfo`.

To use that same logged-in flow, run:

```bash
python3 scraper.py --auth-state jobhai_auth.json --include-recruiter-contact
```

This option is intentionally separate because it may send job applications or
record call activity on the logged-in account. The script only decrypts the
phone number when JobHai returns `call_allowed: true`.

If JobHai returns an encrypted `job_contact` token but marks `call_allowed:
false` because calling is outside the active window, use this assignment-mode
command:

```bash
python3 scraper.py --auth-state jobhai_auth.json --include-recruiter-contact --decrypt-contact-token
```

Use this only for your own assignment/testing account because it still uses the
logged-in Call HR flow and may record application/call activity.

## Run the webapp

```bash
python3 webapp.py
```

Open `http://127.0.0.1:5000`, then click **Load Jobs**.
