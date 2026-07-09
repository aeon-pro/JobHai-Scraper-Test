from flask import Flask, jsonify, render_template_string

from scraper import ScraperError, scrape_jobs


app = Flask(__name__)


HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>JobHai Jaipur Job Scraper</title>
    <style>
      :root {
        color-scheme: light;
        --ink: #17202a;
        --muted: #627080;
        --line: #d8dee6;
        --surface: #ffffff;
        --page: #f5f7fa;
        --accent: #0f766e;
        --accent-dark: #0b5c56;
        --warning: #b45309;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        min-height: 100vh;
        background: var(--page);
        color: var(--ink);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
          BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      a { color: inherit; }

      .shell {
        width: min(1120px, calc(100% - 32px));
        margin: 0 auto;
        padding: 32px 0 48px;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        padding: 26px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 14px 34px rgba(23, 32, 42, 0.08);
      }

      .eyebrow {
        margin: 0 0 8px;
        color: var(--warning);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      h1 {
        margin: 0;
        font-size: clamp(1.9rem, 4vw, 3rem);
        line-height: 1.05;
        letter-spacing: 0;
      }

      .summary {
        max-width: 650px;
        margin: 12px 0 0;
        color: var(--muted);
        line-height: 1.55;
      }

      button {
        flex: 0 0 auto;
        min-width: 136px;
        min-height: 46px;
        border: 0;
        border-radius: 8px;
        background: var(--accent);
        color: white;
        cursor: pointer;
        font-weight: 800;
        font-size: 0.98rem;
      }

      button:hover:not(:disabled) { background: var(--accent-dark); }
      button:disabled { cursor: wait; opacity: 0.68; }

      #status {
        min-height: 24px;
        margin: 18px 0;
        color: var(--muted);
      }

      #jobs {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
        gap: 16px;
      }

      .job-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 18px;
      }

      .job-card-header {
        display: grid;
        grid-template-columns: 44px minmax(0, 1fr);
        gap: 14px;
        align-items: start;
      }

      .rank {
        display: inline-grid;
        width: 44px;
        height: 44px;
        place-items: center;
        border-radius: 8px;
        background: #e6f4f1;
        color: var(--accent-dark);
        font-weight: 900;
      }

      h2 {
        margin: 0;
        font-size: 1.1rem;
        line-height: 1.28;
        letter-spacing: 0;
      }

      .company {
        margin: 6px 0 0;
        color: var(--muted);
      }

      .meta-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-top: 16px;
      }

      .meta-item {
        min-height: 64px;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfcfd;
      }

      .meta-item span {
        display: block;
        color: var(--muted);
        font-size: 0.76rem;
        font-weight: 700;
      }

      .meta-item strong {
        display: block;
        margin-top: 4px;
        overflow-wrap: anywhere;
        font-size: 0.92rem;
        line-height: 1.3;
      }

      .details {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 16px 0 0;
        padding: 0;
        list-style: none;
      }

      .details li {
        padding: 7px 9px;
        border-radius: 8px;
        background: #f0f4f8;
        color: #334155;
        font-size: 0.84rem;
      }

      @media (max-width: 720px) {
        .shell {
          width: min(100% - 20px, 1120px);
          padding-top: 16px;
        }

        .header {
          display: grid;
          padding: 20px;
        }

        button { width: 100%; }
        #jobs, .meta-grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">JobHai Jaipur</p>
          <h1>JobHai Jaipur Job Scraper</h1>
          <p class="summary">
            Load the current top 10 jobs from JobHai and view the details found
            on the listing page.
          </p>
        </div>
        <button id="loadJobs" type="button" data-endpoint="/api/jobs">Load Jobs</button>
      </section>

      <section id="status" aria-live="polite">Ready to scrape.</section>
      <section id="jobs" aria-label="Scraped jobs"></section>
    </main>

    <script>
      const loadButton = document.querySelector("#loadJobs");
      const statusText = document.querySelector("#status");
      const jobsContainer = document.querySelector("#jobs");

      function text(value) {
        return value || "Not listed";
      }

      function addText(parent, tagName, value, className) {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        element.textContent = text(value);
        parent.appendChild(element);
        return element;
      }

      function addDetail(parent, label, value) {
        const item = document.createElement("div");
        item.className = "meta-item";
        addText(item, "span", label);
        addText(item, "strong", value);
        parent.appendChild(item);
      }

      function renderJob(job, index) {
        const card = document.createElement("article");
        card.className = "job-card";

        const header = document.createElement("div");
        header.className = "job-card-header";
        addText(header, "span", String(index + 1).padStart(2, "0"), "rank");

        const titleWrap = document.createElement("div");
        const title = document.createElement("h2");
        const link = document.createElement("a");
        link.textContent = text(job.title);
        link.href = /^https?:\\/\\//i.test(job.link || "") ? job.link : "#";
        link.target = "_blank";
        link.rel = "noreferrer";
        title.appendChild(link);
        titleWrap.appendChild(title);
        addText(titleWrap, "p", job.company, "company");
        header.appendChild(titleWrap);
        card.appendChild(header);

        const meta = document.createElement("div");
        meta.className = "meta-grid";
        addDetail(meta, "Salary", job.salary);
        addDetail(meta, "Location", job.location);
        addDetail(meta, "Experience", job.experience);
        addDetail(meta, "Type", job.jobType);
        addDetail(meta, "Posted", job.posted);
        card.appendChild(meta);

        if (job.details && job.details.length) {
          const details = document.createElement("ul");
          details.className = "details";
          details.setAttribute("aria-label", `Details for ${text(job.title)}`);
          job.details.forEach((detail) => addText(details, "li", detail));
          card.appendChild(details);
        }

        return card;
      }

      async function loadJobs() {
        loadButton.disabled = true;
        loadButton.textContent = "Loading...";
        statusText.textContent = "Starting headless browser scrape...";
        jobsContainer.replaceChildren();

        try {
          const response = await fetch(loadButton.dataset.endpoint);
          const payload = await response.json();

          if (!response.ok) {
            throw new Error(payload.error || "Scrape failed");
          }

          jobsContainer.replaceChildren(...payload.jobs.map(renderJob));
          statusText.textContent = `Loaded ${payload.count} jobs from JobHai.`;
        } catch (error) {
          statusText.textContent = error.message;
        } finally {
          loadButton.disabled = false;
          loadButton.textContent = "Load Jobs";
        }
      }

      loadButton.addEventListener("click", loadJobs);
    </script>
  </body>
</html>
"""


def run_scraper():
    return scrape_jobs()


@app.get("/")
def index():
    return render_template_string(HTML)


@app.get("/api/jobs")
def jobs():
    try:
        scraped_jobs = run_scraper()
    except ScraperError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"count": len(scraped_jobs), "jobs": scraped_jobs})


if __name__ == "__main__":
    app.run(debug=True)
