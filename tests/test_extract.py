from pathlib import Path

from parser import extract_jobs


FIXTURE = Path(__file__).parent / "fixtures" / "jobhai-jaipur.html"
BASE_URL = "https://www.jobhai.com/jobs-in-jaipur-cty"


def test_extracts_first_ten_job_cards_with_page_details():
    jobs = extract_jobs(FIXTURE.read_text(), base_url=BASE_URL, limit=10)

    assert len(jobs) == 10
    assert jobs[0] == {
        "title": "Telecaller",
        "company": "Acme Hiring",
        "location": "Mansarovar, Jaipur",
        "salary": "Rs 18,000 - Rs 25,000 per month",
        "jobType": "Full Time",
        "experience": "0 - 2 years",
        "posted": "Posted 1 day ago",
        "link": "https://www.jobhai.com/job/telecaller-1",
        "details": [
            "Full Time",
            "0 - 2 years",
            "Rs 18,000 - Rs 25,000 per month",
            "Mansarovar, Jaipur",
            "Posted 1 day ago",
        ],
    }
    assert jobs[9]["title"] == "Security Guard"


def test_extracts_real_srp_cards_and_ignores_locality_links():
    html = """
    <div class="carousel_slideItem__O1_xh">
      <a href="https://www.jobhai.com/jobs-in-mansarovar-jaipur-lcty">
        Jobs in Mansarovar , Jaipur (316)
      </a>
    </div>
    <div class="srpCard_card__rWzD6">
      <section class="srpCard_titleContainer__Q4cfz">
        <a href="/delivery-delivery-executive-job-in-blinkit-awadhpuri-jaipur-0-to-6-plus-years-1783580108-7933985-jid">
          Delivery Executive
        </a>
      </section>
      <div>Rs 45,000 - 65,000 per month</div>
      <div>Blinkit</div>
      <div>Awadhpuri, Jaipur</div>
      <div>Flexible shift</div>
      <div>Below 10th</div>
      <p>
        Blinkit is actively hiring for the position of Delivery Executive.
        This role is open to candidates with up to 0 - 6+ years of experience.
      </p>
    </div>
    """

    jobs = extract_jobs(html, base_url=BASE_URL, limit=10)

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Delivery Executive"
    assert jobs[0]["company"] == "Blinkit"
    assert jobs[0]["location"] == "Awadhpuri, Jaipur"
    assert jobs[0]["salary"] == "Rs 45,000 - 65,000 per month"
    assert jobs[0]["experience"] == "0 - 6+ years"
    assert jobs[0]["link"].endswith("-jid")
