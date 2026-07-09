# JobHai Jaipur Scraper

Small Flask app that uses Python Playwright to fetch JobHai's Jaipur jobs page,
parses the returned HTML, and renders the top 10 jobs in the browser.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The scraper uses the `get_html()` helper in `test.py`, which launches installed
Google Chrome through Playwright. If Chrome is not installed, run
`python3 -m playwright install chromium` and change `channel="chrome"` in
`test.py` to the bundled Chromium launcher.

## Run

```bash
python3 app.py
```

Open `http://127.0.0.1:5000`, then click **Load Jobs**.

## Tests

```bash
python3 -m pytest -q
```
