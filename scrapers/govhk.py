"""HK Government civil-service job vacancies scraper (GovHK).

Source: Civil Service Bureau "Government Vacancies Enquiry System" (JVE).
This is a plain HTML table listing of ALL currently advertised vacancies, so
there is no keyword search -- every vacancy is scraped and assigned a Chinese
`label` category by keyword-matching its job title.
"""
import asyncio
from playwright.async_api import async_playwright

# Text-only listing page (one flat HTML table of every current vacancy).
LIST_URL = "https://csboa2.csb.gov.hk/csboa/jve/JVE_001_text.action?languageType=2"
DETAIL_BASE = "https://csboa2.csb.gov.hk/csboa/jve/JVE_003_text.action?jobid={}&languageType=2"
SOURCE = "GovHK"
DEFAULT_COMPANY = "Government of HKSAR"

# label -> English keywords to match in the job title (order = priority).
LABEL_RULES = [
    ("翻译",   ["translation", "translator"]),
    ("法律辅助", ["legal", "paralegal"]),
    ("英语教学", ["teacher", "teaching"]),
    ("公关PR", ["public relations", "information"]),
    ("研究",   ["research"]),
    ("管培生", ["trainee"]),
    ("项目",   ["project", "programme"]),
    ("市场",   ["marketing"]),
    ("文案",   ["writer"]),
    ("编辑",   ["editor"]),
    ("内容",   ["content"]),
    ("统筹",   ["coordinator"]),
    ("运营",   ["operations"]),
    ("行政",   ["administrative", "clerical", "executive officer"]),
    ("助理",   ["assistant", "officer"]),
]
DEFAULT_LABEL = "行政"  # default for government clerical roles


def classify(title):
    """Return the Chinese category label matched from a job title."""
    t = (title or "").lower()
    for label, keywords in LABEL_RULES:
        if any(kw in t for kw in keywords):
            return label
    return DEFAULT_LABEL


def _clean(text):
    """Collapse whitespace from a cell of text."""
    return " ".join((text or "").split()).strip()


async def scrape_listing(page):
    """Parse the flat vacancy table on the JVE text listing page."""
    jobs = []
    rows = await page.query_selector_all("tr")
    for row in rows:
        cells = await row.query_selector_all("td")
        # Each vacancy row has exactly 8 cells:
        # department, title, job-number, salary, academic-req,
        # posting-date, closing-date, application-status.
        if len(cells) != 8:
            continue
        link = await row.query_selector("a[href*='JVE_003']")
        if not link:
            continue

        vals = [_clean(await c.inner_text()) for c in cells]
        department, title, job_no, salary = vals[0], vals[1], vals[2], vals[3]
        posting_date, closing_date = vals[5], vals[6]
        if not title or not job_no:
            continue

        # Prefer the explicit job id from the detail link.
        href = await link.get_attribute("href") or ""
        job_id = job_no
        if "jobid=" in href:
            job_id = href.split("jobid=")[1].split("&")[0]
        url = DETAIL_BASE.format(job_id)

        # posted 必须是「刊登日期」，不能用截止日期（那不是发布日）。
        # 截止日期并入描述，作为求职者参考的「截止」信息。
        posted = posting_date
        snippet = vals[4]  # academic requirement
        if closing_date and "year round" not in closing_date.lower():
            snippet = (snippet + "  ·  截止 " + closing_date).strip()

        jobs.append({
            "title": title,
            "url": url,
            "company": department or DEFAULT_COMPANY,
            "location": "Hong Kong",
            "salary": salary,
            "snippet": snippet,
            "posted": posted,
            "source": SOURCE,
            "label": classify(title),
        })
    return jobs


async def run(max_pages=2):
    """Scrape all current HK government civil-service vacancies.

    The JVE listing is a single page containing every current vacancy, so
    `max_pages` is accepted for interface compatibility but not needed.
    Returns a list of job dicts; returns [] gracefully on any failure.
    """
    all_jobs, seen = [], set()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                ctx = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="en-HK",
                    viewport={"width": 1280, "height": 900},
                )
                page = await ctx.new_page()
                print(f"  [GovHK] {LIST_URL}")
                await page.goto(LIST_URL, wait_until="networkidle", timeout=60000)
                try:
                    await page.wait_for_selector("a[href*='JVE_003']", timeout=15000)
                except Exception:
                    pass

                jobs = await scrape_listing(page)
                for j in jobs:
                    u = j.get("url", "")
                    if u and u not in seen:
                        seen.add(u)
                        all_jobs.append(j)
                print(f"    found {len(all_jobs)} vacancies")
            finally:
                await browser.close()
    except Exception as e:
        print(f"  GovHK error: {e}")
        return []
    print(f"  GovHK total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
