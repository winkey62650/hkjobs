"""Glassdoor HK scraper

Glassdoor sits behind Cloudflare and shows sign-in / job-alert modals.
Mitigations used here:
  - realistic desktop user-agent + en-HK locale
  - a FRESH browser context per category (Cloudflare 403s repeated hits
    that reuse a context too quickly)
  - a polite delay between categories
  - dismiss the sign-in / job-alert modal if it appears
  - "pages" are fetched by clicking the in-page "load more" button,
    because Glassdoor uses infinite-scroll rather than _IP URLs.

The HK location is location id IN106. Search URL format:
  /Job/hong-kong-<kw>-jobs-SRCH_IL.0,9_IN106_KO10,<10+len(kw)>.htm
"""
import asyncio
import html
import re
from playwright.async_api import async_playwright

BASE   = "https://www.glassdoor.com.hk"
SOURCE = "Glassdoor"

# label -> English keyword used in the URL slug
GROUPS = [
    ("assistant",            "助理"),
    ("operations",           "运营"),
    ("administration",       "行政"),
    ("coordinator",          "统筹"),
    ("content",              "内容"),
    ("copywriter",           "文案"),
    ("editor",               "编辑"),
    ("public-relations",     "公关PR"),
    ("research",             "研究"),
    ("management-trainee",   "管培生"),
    ("programme-officer",    "项目"),
    ("marketing",            "市场"),
    ("english-teacher",      "英语教学"),
    ("paralegal",            "法律辅助"),
    ("translator",           "翻译"),
]
MAX_PAGES = 2

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# delay (seconds) between categories to stay under Cloudflare's radar
CATEGORY_DELAY = 8


def build_url(kw):
    """Search URL for a keyword, HK location (IN106)."""
    end = 10 + len(kw)
    return f"{BASE}/Job/hong-kong-{kw}-jobs-SRCH_IL.0,9_IN106_KO10,{end}.htm"


async def dismiss_modal(page):
    """Best-effort close of the sign-in / job-alert modal."""
    selectors = [
        "button[data-test='job-alert-modal-close']",
        "[data-test='modal-close']",
        ".modal_closeIcon__y_d3W",
        "button[aria-label='Close']",
        "span[alt='Close']",
        ".CloseButton",
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click(timeout=3000)
                await page.wait_for_timeout(500)
        except Exception:
            pass
    # ESC as a fallback
    try:
        await page.keyboard.press("Escape")
    except Exception:
        pass


async def extract_cards(page):
    """Extract job dicts from the currently loaded job-listing cards."""
    jobs = []
    cards = await page.query_selector_all("li[data-test='jobListing']")
    for c in cards:
        j = {k: "" for k in
             ("title", "url", "company", "location", "salary",
              "snippet", "posted", "source", "label")}
        j["source"] = SOURCE

        a = await c.query_selector("a[data-test='job-title']")
        if not a:
            continue
        try:
            j["title"] = (await a.inner_text()).strip()
        except Exception:
            continue
        href = await a.get_attribute("href") or ""
        if not href:
            continue
        j["url"] = href if href.startswith("http") else BASE + href
        # strip tracking query for a stable dedup key
        j["url"] = j["url"].split("?")[0]

        for sel, key in [
            (".EmployerProfile_compactEmployerName__9MGcV", "company"),
            ("[data-test='emp-location']",                  "location"),
            ("[data-test='detailSalary']",                  "salary"),
            (".JobCard_jobDescriptionSnippet__l1tnl",        "snippet"),
            ("[data-test='job-age']",                       "posted"),
        ]:
            el = await c.query_selector(sel)
            if el:
                try:
                    txt = (await el.inner_text()).strip()
                    # tidy up HTML entities / collapse whitespace
                    txt = html.unescape(txt)
                    txt = re.sub(r"\s+", " ", txt).strip()
                    j[key] = txt
                except Exception:
                    pass
        jobs.append(j)
    return jobs


async def scrape_category(browser, kw, label, max_pages):
    """Open a fresh context, load the category, click 'load more' to
    emulate paging, and return job dicts."""
    ctx = await browser.new_context(
        user_agent=UA, locale="en-HK",
        viewport={"width": 1366, "height": 900})
    page = await ctx.new_page()
    jobs = []
    try:
        resp = await page.goto(build_url(kw), wait_until="domcontentloaded",
                               timeout=45000)
        await page.wait_for_timeout(5000)
        status = resp.status if resp else None
        title = await page.title()
        if status != 200:
            print(f"    blocked (status {status})")
            return jobs
        if "just a moment" in title.lower() or "security" in title.lower():
            print("    blocked (Cloudflare challenge page)")
            return jobs

        try:
            await page.wait_for_selector("li[data-test='jobListing']",
                                         timeout=15000)
        except Exception:
            pass

        jobs = await extract_cards(page)
        if not jobs:
            print(f"    no cards (status {status}, title='{title[:50]}')")
        await dismiss_modal(page)

        # extra "pages": click "load more", then re-extract the full list.
        # Keep whichever extraction yielded the most cards so a failed
        # click (which can briefly empty the DOM) never loses results.
        for _ in range(max_pages - 1):
            try:
                btn = await page.query_selector("[data-test='load-more']")
                if not btn or not await btn.is_visible():
                    break
                await dismiss_modal(page)
                await btn.click(timeout=5000)
                await page.wait_for_timeout(4000)
                await dismiss_modal(page)
                more = await extract_cards(page)
                if len(more) > len(jobs):
                    jobs = more
            except Exception:
                break
    except Exception as e:
        print(f"    error: {repr(e)[:140]}")
    finally:
        try:
            await ctx.close()
        except Exception:
            pass
    return jobs


async def run(max_pages=MAX_PAGES):
    all_jobs, seen = [], set()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                for i, (kw, label) in enumerate(GROUPS):
                    print(f"  [Glassdoor/{label}] {kw}")
                    jobs = await scrape_category(browser, kw, label, max_pages)
                    new = 0
                    for j in jobs:
                        u = j.get("url", "")
                        if u and u not in seen:
                            seen.add(u)
                            j["label"] = label
                            all_jobs.append(j)
                            new += 1
                    print(f"    +{new} ({len(jobs)} cards seen)")
                    if i < len(GROUPS) - 1:
                        await asyncio.sleep(CATEGORY_DELAY)
            finally:
                await browser.close()
    except Exception as e:
        print(f"  Glassdoor fatal error: {repr(e)[:160]}")
    print(f"  Glassdoor total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
