const loadButton = document.querySelector("#loadJobs");
const statusText = document.querySelector("#statusText");
const jobsContainer = document.querySelector("#jobs");

function setLoading(isLoading) {
  loadButton.disabled = isLoading;
  loadButton.textContent = isLoading ? "Loading..." : "Load Jobs";
}

function valueOrFallback(value) {
  return value || "Not listed";
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = valueOrFallback(value);
  return node.innerHTML;
}

function renderDetail(label, value) {
  return `
    <div class="meta-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderJob(job, index) {
  const detailItems = (job.details || [])
    .map((detail) => `<li>${escapeHtml(detail)}</li>`)
    .join("");
  const title = escapeHtml(job.title);
  const link = job.link || "#";
  const safeLink = /^https?:\/\//i.test(link) ? link : "#";

  return `
    <article class="job-card">
      <div class="job-card-header">
        <span class="rank">${String(index + 1).padStart(2, "0")}</span>
        <div>
          <h2><a href="${safeLink}" target="_blank" rel="noreferrer">${title}</a></h2>
          <p>${escapeHtml(job.company)}</p>
        </div>
      </div>
      <div class="meta-grid">
        ${renderDetail("Salary", job.salary)}
        ${renderDetail("Location", job.location)}
        ${renderDetail("Experience", job.experience)}
        ${renderDetail("Type", job.jobType)}
        ${renderDetail("Posted", job.posted)}
      </div>
      ${
        detailItems
          ? `<ul class="details-list" aria-label="Details for ${title}">${detailItems}</ul>`
          : ""
      }
    </article>
  `;
}

async function loadJobs() {
  const endpoint = loadButton.dataset.endpoint;
  setLoading(true);
  statusText.textContent = "Starting headless browser scrape...";
  jobsContainer.innerHTML = "";

  try {
    const response = await fetch(endpoint);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Scrape failed");
    }

    jobsContainer.innerHTML = payload.jobs.map(renderJob).join("");
    statusText.textContent = `Loaded ${payload.count} jobs from JobHai.`;
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    setLoading(false);
  }
}

loadButton.addEventListener("click", loadJobs);
