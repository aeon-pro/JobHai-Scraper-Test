from flask import Flask, jsonify, render_template

from scraper.jobhai import ScraperError, scrape_jobs

app = Flask(__name__)


def run_scraper():
    return scrape_jobs()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/jobs")
def jobs():
    try:
        scraped_jobs = run_scraper()
    except ScraperError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"count": len(scraped_jobs), "jobs": scraped_jobs})


if __name__ == "__main__":
    app.run(debug=True)
