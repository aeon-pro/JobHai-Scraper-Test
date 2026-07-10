import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


CARD_SELECTORS = [
    '[data-testid="job-card"]',
    '[data-test*="job"]',
    "[data-job-id]",
    '[class*="srpCard_card"]',
    "article",
    ".job-card",
    ".jobCard",
    '[class*="job-card"]',
    '[class*="jobCard"]',
    '[class*="JobCard"]',
    'li[class*="job"]',
]

TITLE_SELECTORS = [
    ".job-title",
    '[data-testid*="title"]',
    '[class*="titleContainer"]',
    '[class*="TitleContainer"]',
    '[class*="title"]',
    '[class*="job-title"]',
    '[class*="jobTitle"]',
    '[class*="JobTitle"]',
    "h1",
    "h2",
    "h3",
    'a[href*="/job"]',
]

FIELD_SELECTORS = {
    "company": [
        ".company-name",
        '[data-testid*="company"]',
        '[class*="company-name"]',
        '[class*="companyName"]',
        '[class*="Company"]',
        '[class*="company"]',
    ],
    "salary": [
        ".salary",
        '[data-testid*="salary"]',
        '[class*="salary"]',
        '[class*="Salary"]',
    ],
    "jobType": [
        ".job-type",
        '[data-testid*="job-type"]',
        '[class*="job-type"]',
        '[class*="jobType"]',
        '[class*="JobType"]',
    ],
    "experience": [
        ".experience",
        '[data-testid*="experience"]',
        '[class*="experience"]',
        '[class*="Experience"]',
        '[class*="exp"]',
    ],
    "location": [
        ".location",
        '[data-testid*="location"]',
        '[class*="location"]',
        '[class*="Location"]',
        '[class*="locality"]',
    ],
    "posted": [
        ".posted",
        '[data-testid*="posted"]',
        '[class*="posted"]',
        '[class*="Posted"]',
        '[class*="date"]',
        '[class*="Date"]',
        '[class*="time"]',
    ],
}

DESCRIPTION_SELECTORS = [
    '[class*="jobDescription"]',
    '[class*="JobDescription"]',
    '[class*="description"]',
    '[class*="Description"]',
    '[data-testid*="description"]',
    '[data-test*="description"]',
]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<![\d.])(?:\+?91[\s-]*)?[6-9](?:[\s-]*\d){9}(?![\d.])")


def normalise_whitespace(value):
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def unique(items):
    seen = set()
    output = []

    for item in items:
        value = normalise_whitespace(item)
        key = value.lower()
        if not value or key in seen:
            continue

        seen.add(key)
        output.append(value)

    return output


def clean_soup(soup):
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    return soup


def first_text(parent, selectors):
    for selector in selectors:
        element = parent.select_one(selector)
        if element:
            text = normalise_whitespace(element.get_text(" ", strip=True))
            if text:
                return text

    return ""


def card_lines(card):
    return unique(card.get_text("\n", strip=True).splitlines())


def matches_any_line(lines, predicate):
    return next((line for line in lines if predicate(line)), "")


def is_salary(line):
    return bool(
        re.search(
            r"(rs\.?|inr|₹|\blpa\b|salary|per\s+month|per\s+annum|/month)",
            line,
            re.I,
        )
    )


def is_experience(line):
    return bool(
        re.search(
            r"(fresher|experience|exp\.?|\d+\s*[-+to]*\s*\d*\s*(years?|yrs?))",
            line,
            re.I,
        )
    )


def is_job_type(line):
    return bool(
        re.search(
            r"(full\s*time|part\s*time|work\s+from\s+home|contract|internship|night\s+shift)",
            line,
            re.I,
        )
    )


def is_posted(line):
    return bool(
        re.search(
            r"(posted|today|yesterday|\d+\s+(days?|weeks?|months?)\s+ago)",
            line,
            re.I,
        )
    )


def is_location(line):
    return bool(
        re.search(
            r"(jaipur|mansarovar|vaishali|malviya|jhotwara|sodala|tonk|ajmer|jagatpura|bani\s+park|c\s+scheme)",
            line,
            re.I,
        )
    )


def is_full_time_job(job):
    values = [
        job.get("jobType", ""),
        " ".join(job.get("details", [])),
        job.get("jobDescription", ""),
    ]
    text = " ".join(values).lower()

    return "full time" in text or "full-time" in text


def field_from_selectors_or_lines(card, lines, key, predicate):
    return first_text(card, FIELD_SELECTORS[key]) or matches_any_line(lines, predicate)


def short_field_from_selectors_or_lines(card, lines, key, predicate):
    value = first_text(card, FIELD_SELECTORS[key])
    if value:
        return value

    return matches_any_line(
        lines,
        lambda line: is_compact_detail_line(line) and predicate(line),
    )


def is_compact_detail_line(line):
    return bool(
        len(line) <= 70
        and "." not in line
        and not re.search(
            r"\b(actively|candidate|candidates|position|qualify|role|vacancy)\b",
            line,
            re.I,
        )
    )


def is_job_detail_href(href):
    path = urlparse(href).path
    if not path:
        return False

    if "jobs-in-" in path or path.endswith("-ccty") or path.endswith("-ccmp"):
        return False

    return bool(
        path.endswith("-jid")
        or "/job/" in path
        or re.search(r"-job-in-.+-\d+", path)
    )


def find_job_link(card):
    for anchor in card.select("a[href]"):
        if is_job_detail_href(anchor.get("href", "")):
            return anchor

    return None


def experience_from_href(href):
    path = urlparse(href or "").path
    match = re.search(r"-(\d+)-to-(\d+)(-plus)?-years-", path)
    if not match:
        return ""

    start, end, plus = match.groups()
    suffix = "+" if plus else ""
    return f"{start} - {end}{suffix} years"


def title_from_card(card, lines, link):
    selector_title = first_text(card, TITLE_SELECTORS)
    if selector_title:
        return selector_title

    if link:
        link_title = normalise_whitespace(link.get_text(" ", strip=True))
        if link_title:
            return link_title

    return next(
        (
            line
            for line in lines
            if not is_salary(line)
            and not is_experience(line)
            and not is_job_type(line)
            and not is_posted(line)
            and not is_location(line)
        ),
        "",
    )


def company_from_card(card, lines, title, known_details):
    selector_company = first_text(card, FIELD_SELECTORS["company"])
    if selector_company and selector_company != title:
        return selector_company

    return next(
        (
            line
            for line in lines
            if line != title
            and line not in known_details
            and "apply" not in line.lower()
            and "view" not in line.lower()
            and "job" not in line.lower()
            and not is_salary(line)
            and not is_experience(line)
            and not is_job_type(line)
            and not is_posted(line)
            and not is_location(line)
        ),
        "",
    )


def extract_job_card(card, base_url):
    lines = card_lines(card)
    link = find_job_link(card)
    href = link.get("href") if link else ""
    title = title_from_card(card, lines, link)
    salary = field_from_selectors_or_lines(card, lines, "salary", is_salary)
    job_type = field_from_selectors_or_lines(card, lines, "jobType", is_job_type)
    experience = short_field_from_selectors_or_lines(
        card,
        lines,
        "experience",
        is_experience,
    ) or experience_from_href(href)
    location = field_from_selectors_or_lines(card, lines, "location", is_location)
    posted = field_from_selectors_or_lines(card, lines, "posted", is_posted)
    details = unique([job_type, experience, salary, location, posted])
    company = company_from_card(card, lines, title, details)

    return {
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "jobType": job_type,
        "experience": experience,
        "posted": posted,
        "link": urljoin(base_url, href),
        "details": details,
    }


def query_unique(soup, selectors):
    elements = []
    seen = set()

    for selector in selectors:
        for element in soup.select(selector):
            key = id(element)
            if key in seen:
                continue

            seen.add(key)
            elements.append(element)

    return elements


def nearest_card_container(anchor):
    for parent in anchor.parents:
        classes = " ".join(parent.get("class", []))
        if "srpCard_card" in classes:
            return parent

    return anchor.find_parent(["article", "li", "section", "div"])


def anchor_card_fallback(soup):
    cards = []
    seen = set()

    for anchor in soup.select("a[href]"):
        if not is_job_detail_href(anchor.get("href", "")):
            continue

        card = nearest_card_container(anchor)
        if card is None:
            continue

        key = id(card)
        if key in seen:
            continue

        seen.add(key)
        cards.append(card)

    return cards


def is_likely_job_card(card):
    text = normalise_whitespace(card.get_text(" ", strip=True))
    if len(text) < 20:
        return False

    return bool(
        find_job_link(card)
        or is_salary(text)
        or re.search(r"full\s*time|part\s*time|fresher|experience", text, re.I)
    )


def text_from_selectors(soup, selectors):
    for selector in selectors:
        for element in soup.select(selector):
            text = normalise_whitespace(element.get_text(" ", strip=True))
            if len(text) >= 20:
                return text

    return ""


def text_after_heading(soup, heading_patterns):
    for element in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
        heading = normalise_whitespace(element.get_text(" ", strip=True))
        if not any(re.search(pattern, heading, re.I) for pattern in heading_patterns):
            continue

        parent = element.find_parent(["section", "article", "div"]) or element.parent
        if parent:
            text = normalise_whitespace(parent.get_text(" ", strip=True))
            if len(text) >= 20:
                return text

    return ""


def value_after_heading(soup, heading_patterns):
    heading_tags = {"h1", "h2", "h3", "h4", "strong", "b"}

    for element in soup.find_all(heading_tags):
        heading = normalise_whitespace(element.get_text(" ", strip=True))
        if not any(re.search(pattern, heading, re.I) for pattern in heading_patterns):
            continue

        values = []
        for sibling in element.next_siblings:
            if getattr(sibling, "name", None) in heading_tags:
                break

            text = normalise_whitespace(
                sibling.get_text(" ", strip=True)
                if hasattr(sibling, "get_text")
                else sibling
            )
            if text:
                values.append(text)

        if values:
            return " ".join(values)

        parent = element.find_parent(["section", "article", "div"]) or element.parent
        if parent:
            text = normalise_whitespace(parent.get_text(" ", strip=True))
            value = re.sub(re.escape(heading), "", text, count=1).strip(" :-")
            if value:
                return value

    return "Not available"


def visible_text(html):
    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    return normalise_whitespace(soup.get_text(" ", strip=True))


def extract_phone(text):
    for match in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 12 and digits.startswith("91"):
            return f"+91 {digits[2:]}"
        if len(digits) == 10 and digits[0] in "6789":
            return f"+91 {digits}"

    return "Not available"


def extract_email(text):
    match = EMAIL_RE.search(text)
    return match.group(0) if match else "Not available"


def extract_job_detail(html):
    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    page_text = normalise_whitespace(soup.get_text(" ", strip=True))
    description = (
        text_from_selectors(soup, DESCRIPTION_SELECTORS)
        or text_after_heading(soup, [r"job\s+description", r"about\s+.*job"])
        or page_text
    )

    return {
        "jobDescription": description,
        "contactPerson": value_after_heading(soup, [r"contact\s+person"]),
        "recruiterPhone": extract_phone(page_text),
        "recruiterEmail": extract_email(page_text),
    }


def extract_jobs(html, base_url, limit=10, full_time_only=False):
    soup = clean_soup(BeautifulSoup(html, "html.parser"))
    primary_cards = [
        card for card in query_unique(soup, CARD_SELECTORS) if is_likely_job_card(card)
    ]
    cards = primary_cards or anchor_card_fallback(soup)
    jobs = []
    seen = set()

    for card in cards:
        job = extract_job_card(card, base_url)
        if not job["title"]:
            continue

        if full_time_only and not is_full_time_job(job):
            continue

        key = "|".join(
            [job["title"], job["company"], job["location"], job["link"]]
        ).lower()
        if key in seen:
            continue

        seen.add(key)
        jobs.append(job)

        if len(jobs) >= limit:
            break

    return jobs
