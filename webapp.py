import csv
from pathlib import Path

from flask import Flask, jsonify, render_template_string

from scraper import CSV_COLUMNS, ScraperError, job_to_csv_row, scrape_jobs


app = Flask(__name__)
OUTPUT_CSV = Path("jobhai_jaipur_jobs.csv")


HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>JobHai Jaipur Jobs</title>
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
        --soft: #eef7f5;
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
        width: min(1440px, calc(100% - 32px));
        margin: 0 auto;
        padding: 24px 0 48px;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        padding: 22px 24px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
      }

      .eyebrow {
        margin: 0 0 6px;
        color: var(--warning);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }

      h1 {
        margin: 0;
        font-size: 1.75rem;
        line-height: 1.15;
        letter-spacing: 0;
      }

      .summary {
        max-width: 760px;
        margin: 10px 0 0;
        color: var(--muted);
        line-height: 1.5;
      }

      button {
        flex: 0 0 auto;
        min-width: 136px;
        min-height: 44px;
        border: 0;
        border-radius: 8px;
        background: var(--accent);
        color: white;
        cursor: pointer;
        font-weight: 800;
        font-size: 0.95rem;
      }

      button:hover:not(:disabled) { background: var(--accent-dark); }
      button:disabled { cursor: wait; opacity: 0.68; }

      .status-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        min-height: 44px;
        margin: 14px 0;
        color: var(--muted);
      }

      .count-pill {
        display: inline-flex;
        align-items: center;
        min-height: 30px;
        padding: 4px 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        color: var(--ink);
        font-weight: 700;
      }

      .table-wrap {
        overflow-x: auto;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 8px;
      }

      table {
        width: 100%;
        min-width: 1180px;
        border-collapse: collapse;
      }

      th,
      td {
        padding: 12px;
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
        font-size: 0.9rem;
        line-height: 1.4;
      }

      th {
        position: sticky;
        top: 0;
        z-index: 1;
        background: #f8fafc;
        color: #334155;
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
      }

      tbody tr:last-child td { border-bottom: 0; }
      tbody tr:hover { background: #fbfcfd; }

      .rank {
        width: 48px;
        color: var(--accent-dark);
        font-weight: 900;
      }

      .job-title {
        display: inline-block;
        max-width: 290px;
        color: var(--accent-dark);
        font-weight: 850;
        text-decoration: none;
      }

      .job-title:hover { text-decoration: underline; }

      .company {
        margin-top: 5px;
        color: var(--muted);
      }

      .job-url {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        padding: 4px 8px;
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--accent-dark);
        font-size: 0.82rem;
        font-weight: 800;
        text-decoration: none;
      }

      .job-url:hover { border-color: var(--accent); }

      .contact-line {
        min-width: 190px;
        margin-bottom: 6px;
      }

      .label {
        display: block;
        color: var(--muted);
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
      }

      .value {
        display: block;
        overflow-wrap: anywhere;
      }

      .phone {
        color: var(--accent-dark);
        font-weight: 800;
        text-decoration: none;
      }

      details {
        width: min(420px, 100%);
      }

      summary {
        cursor: pointer;
        color: var(--accent-dark);
        font-weight: 800;
      }

      .description-text {
        max-height: 220px;
        margin: 10px 0 0;
        overflow: auto;
        padding: 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--soft);
        color: #293241;
        white-space: pre-wrap;
      }

      .url-text {
        max-width: 320px;
        margin-top: 10px;
        overflow-wrap: anywhere;
      }

      .empty-state {
        padding: 28px;
        background: var(--surface);
        border: 1px dashed var(--line);
        border-radius: 8px;
        color: var(--muted);
      }

      @media (max-width: 760px) {
        .shell {
          width: min(100% - 20px, 1440px);
          padding-top: 12px;
        }

        .header {
          display: grid;
          padding: 18px;
        }

        button { width: 100%; }

        .status-row {
          display: grid;
          align-items: start;
        }
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">JobHai Jaipur</p>
          <h1>Latest Full-Time Job Records</h1>
          <p class="summary">
            Structured fields from the scraper output, including job
            description, contact person, recruiter phone, email status, and
            source URL.
          </p>
        </div>
        <button id="loadJobs" type="button" data-endpoint="/api/jobs">Load Data</button>
      </section>

      <section class="status-row" aria-live="polite">
        <span id="status">Ready.</span>
        <span id="count" class="count-pill">0 records</span>
      </section>

      <section id="jobs" aria-label="Scraped jobs">
        <div class="empty-state">No jobs loaded.</div>
      </section>
    </main>

    <script>
      const loadButton = document.querySelector("#loadJobs");
      const statusText = document.querySelector("#status");
      const countText = document.querySelector("#count");
      const jobsContainer = document.querySelector("#jobs");

      function text(value) {
        const clean = String(value || "").trim();
        return clean || "Not available";
      }

      function cell(row, key) {
        const td = document.createElement("td");
        td.textContent = text(row[key]);
        return td;
      }

      function contactBlock(label, value, hrefPrefix) {
        const block = document.createElement("div");
        block.className = "contact-line";

        const labelEl = document.createElement("span");
        labelEl.className = "label";
        labelEl.textContent = label;
        block.appendChild(labelEl);

        const clean = text(value);
        if (hrefPrefix && clean !== "Not available") {
          const link = document.createElement("a");
          link.className = hrefPrefix === "tel:" ? "phone value" : "value";
          link.href = hrefPrefix + clean.replace(/\\s+/g, "");
          link.textContent = clean;
          block.appendChild(link);
        } else {
          const valueEl = document.createElement("span");
          valueEl.className = "value";
          valueEl.textContent = clean;
          block.appendChild(valueEl);
        }

        return block;
      }

      function renderExpandableCell(row, key, summaryText) {
        const td = document.createElement("td");
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        const body = document.createElement("div");

        summary.textContent = summaryText;
        body.className = "description-text";
        body.textContent = text(row[key]);

        details.append(summary, body);
        td.appendChild(details);
        return td;
      }

      function renderJobCell(row) {
        const td = document.createElement("td");
        const link = document.createElement("a");
        const company = document.createElement("div");

        link.className = "job-title";
        link.textContent = text(row.job_title);
        link.href = /^https?:\\/\\//i.test(row.job_url || "") ? row.job_url : "#";
        link.target = "_blank";
        link.rel = "noreferrer";

        company.className = "company";
        company.textContent = text(row.company);

        td.append(link, company);
        return td;
      }

      function renderContactCell(row) {
        const td = document.createElement("td");
        td.append(
          contactBlock("Contact person", row.contact_person),
          contactBlock("Phone", row.recruiter_phone, "tel:"),
          contactBlock("Email", row.recruiter_email, "mailto:")
        );
        return td;
      }

      function renderUrlCell(row) {
        const td = document.createElement("td");
        const link = document.createElement("a");
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        const urlText = document.createElement("div");

        link.className = "job-url";
        link.href = /^https?:\\/\\//i.test(row.job_url || "") ? row.job_url : "#";
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = "Open job";

        summary.textContent = "View URL";
        urlText.className = "description-text url-text";
        urlText.textContent = text(row.job_url);
        details.append(summary, urlText);

        td.append(link, details);
        return td;
      }

      function renderTable(rows) {
        const tableWrap = document.createElement("div");
        const table = document.createElement("table");
        const thead = document.createElement("thead");
        const tbody = document.createElement("tbody");
        const headerRow = document.createElement("tr");

        tableWrap.className = "table-wrap";
        [
          "No.",
          "Job",
          "Location",
          "Salary",
          "Type",
          "Experience",
          "Posted",
          "Recruiter",
          "Description",
          "URL",
        ].forEach((heading) => {
          const th = document.createElement("th");
          th.textContent = heading;
          headerRow.appendChild(th);
        });

        rows.forEach((row, index) => {
          const tr = document.createElement("tr");
          const rank = document.createElement("td");
          rank.className = "rank";
          rank.textContent = String(index + 1).padStart(2, "0");

          tr.append(
            rank,
            renderJobCell(row),
            cell(row, "location"),
            cell(row, "salary"),
            renderExpandableCell(row, "job_type", "View type"),
            cell(row, "experience"),
            cell(row, "posted"),
            renderContactCell(row),
            renderExpandableCell(row, "job_description", "View description"),
            renderUrlCell(row)
          );
          tbody.appendChild(tr);
        });

        thead.appendChild(headerRow);
        table.append(thead, tbody);
        tableWrap.appendChild(table);
        return tableWrap;
      }

      async function loadJobs() {
        loadButton.disabled = true;
        loadButton.textContent = "Loading...";
          statusText.textContent = "Loading job records...";
        countText.textContent = "0 records";
        jobsContainer.replaceChildren();

        try {
          const response = await fetch(loadButton.dataset.endpoint);
          const payload = await response.json();

          if (!response.ok) {
            throw new Error(payload.error || "Scrape failed");
          }

          jobsContainer.replaceChildren(renderTable(payload.jobs));
          statusText.textContent = payload.source === "csv"
            ? "Loaded saved CSV output."
            : "Loaded latest Jaipur jobs.";
          countText.textContent = `${payload.count} records`;
        } catch (error) {
          statusText.textContent = error.message;
          countText.textContent = "0 records";
          const empty = document.createElement("div");
          empty.className = "empty-state";
          empty.textContent = "No jobs loaded.";
          jobsContainer.replaceChildren(empty);
        } finally {
          loadButton.disabled = false;
          loadButton.textContent = "Load Data";
        }
      }

      loadButton.addEventListener("click", loadJobs);
    </script>
  </body>
</html>
"""


def load_csv_rows():
    with OUTPUT_CSV.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [
            {column: row.get(column, "Not available") for column in CSV_COLUMNS}
            for row in reader
        ]


def run_scraper():
    if OUTPUT_CSV.exists():
        return load_csv_rows(), "csv"

    jobs = scrape_jobs()
    return [job_to_csv_row(job) for job in jobs], "live"


@app.get("/")
def index():
    return render_template_string(HTML)


@app.get("/api/jobs")
def jobs():
    try:
        rows, source = run_scraper()
    except ScraperError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(
        {"columns": CSV_COLUMNS, "count": len(rows), "jobs": rows, "source": source}
    )


if __name__ == "__main__":
    app.run(debug=True)
