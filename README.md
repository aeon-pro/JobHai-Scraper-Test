# JobHai Jaipur Scraper

A small Python project that scrapes the top JobHai listings for Jaipur and
shows them in a simple Flask webapp.

## Files

- `parser.py` parses JobHai listing HTML into structured job records.
- `scraper.py` loads JobHai with Playwright and prints scraped jobs as JSON.
- `webapp.py` serves a Flask page with a **Load Jobs** button.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install chromium
```

## Run the scraper

```bash
python3 scraper.py
```

Optional:

```bash
python3 scraper.py --limit 5
```

## Run the webapp

```bash
python3 webapp.py
```

Open `http://127.0.0.1:5000`, then click **Load Jobs**.
