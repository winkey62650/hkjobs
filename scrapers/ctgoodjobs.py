"""CTgoodjobs HK scraper

NOTE: CTgoodjobs' job-listing host (jobs.ctgoodjobs.hk) is protected by an
interactive human-verification CAPTCHA. Every listing/search endpoint returns
HTTP 405 with a "Human Verification" challenge ("我们需要确认您是人类") that does
NOT auto-resolve and cannot be passed programmatically. This scraper still
attempts a real search with realistic mitigations (zh-HK locale, realistic
user-agent, webdriver masking, homepage warm-up, domcontentloaded + explicit
wait_for_selector, random delays). When the challenge blocks access it logs the
reason and returns an empty list gracefully instead of crashing.
"""
import asyncio, random
from playwright.async_api import async_playwright

BASE   = "https://jobs.ctgoodjobs.hk"
HOME   = "https://www.ctgoodjobs.hk"
SOURCE = "CTgoodjobs"

GROUPS = [
    ("assistant",            "助理"),
    ("operations",           "运营"),
    ("administration",       "行政"),
    ("coordinator",          "统筹"),
    ("content",              "内容"),
    ("copywriter",           "文案"),
    ("editor",               "编辑"),
    ("public relations",     "公关PR"),
    ("research",             "研究"),
    ("management trainee",   "管培生"),
    ("programme officer",    "项目"),
    ("marketing",            "市场"),
    ("english teacher",      "英语教学"),
    ("paralegal",            "法律辅助"),
    ("translator",           "翻译"),
]
MAX_PAGES = 2

# Job-card selector candidates (the listing host is CAPTCHA-walled, so the
# exact production markup could not be confirmed live; these cover the common
# CTgoodjobs layouts).
CARD_SELECTORS = [
    'div[class*="job-card"]',
    'div[class*="jobListItem"]',
    'article[class*="job"]',
    'li[class*="job-list"]',
]


def _looks_blocked(title: str, body: str) -> bool:
    t = (title or "").lower()
    b = body or ""
    return (
        "human verification" in t
        or "确认您是人类" in b
        or "安全检查" in b
        or "请完成" in b
    )


async def _text(node, selectors):
    """Return inner_text of the first matching child selector, else ''."""
    for sel in selectors:
        try:
            el = await node.query_selector(sel)
            if el:
                txt = (await el.inner_text()).strip()
                if txt:
                    return txt
        except Exception:
            pass
    return ""


async def scrape_page(page, keyword, pg):
    """Scrape one search results page. Returns (jobs, blocked)."""
    url = f"{BASE}/jobs?keyword={keyword.replace(' ', '+')}&page={pg}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print(f"      nav error: {e}")
        return [], False

    await page.wait_for_timeout(random.randint(1500, 3500))

    title = ""
    body = ""
    try:
        title = await page.title()
        body = await page.inner_text("body")
    except Exception:
        pass
    if _looks_blocked(title, body):
        return [], True

    # Wait for any job-card layout to appear.
    cards = []
    for sel in CARD_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=8000)
            cards = await page.query_selector_all(sel)
            if cards:
                break
        except Exception:
            continue
    if not cards:
        return [], False

    jobs = []
    for c in cards:
        try:
            link = await c.query_selector('a[href*="/job/"], a[href*="/jobs/"]')
            if not link:
                continue
            href = await link.get_attribute("href") or ""
            if not href:
                continue
            full = href if href.startswith("http") else BASE + href
            full = full.split("?")[0]

            title_txt = await _text(c, [
                'h2', 'h3', '[class*="title"]', '[class*="jobTitle"]',
            ]) or (await link.inner_text()).strip()

            jobs.append({
                "title":    title_txt,
                "url":      full,
                "company":  await _text(c, ['[class*="company"]', '[class*="employer"]']),
                "location": await _text(c, ['[class*="location"]', '[class*="district"]', '[class*="area"]']),
                "salary":   await _text(c, ['[class*="salary"]', '[class*="pay"]']),
                "snippet":  await _text(c, ['[class*="desc"]', '[class*="snippet"]', '[class*="summary"]', 'p']),
                "posted":   await _text(c, ['[class*="date"]', '[class*="post"]', 'time']),
                "source":   SOURCE,
                "label":    "",
            })
        except Exception:
            continue
    return jobs, False


async def run(max_pages=MAX_PAGES):
    all_jobs, seen = [], set()
    blocked = False
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = await browser.new_context(
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"),
                locale="zh-HK",
                viewport={"width": 1366, "height": 900},
                extra_http_headers={"Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"},
            )
            await ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )
            page = await ctx.new_page()

            # Warm up: load the homepage first to collect cookies.
            try:
                await page.goto(HOME, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(random.randint(2000, 4000))
            except Exception:
                pass

            for keyword, label in GROUPS:
                print(f"  [CTgoodjobs/{label}] {keyword}")
                for pg in range(1, max_pages + 1):
                    jobs, page_blocked = await scrape_page(page, keyword, pg)
                    if page_blocked:
                        blocked = True
                        print("    blocked by human-verification challenge")
                        break
                    if not jobs:
                        break
                    new = 0
                    for j in jobs:
                        u = j.get("url", "")
                        if u and u not in seen:
                            seen.add(u)
                            j["label"] = label
                            all_jobs.append(j)
                            new += 1
                    print(f"    p{pg}: +{new}")
                    if new == 0:
                        break
                    await page.wait_for_timeout(random.randint(800, 2000))
                if blocked:
                    # The whole listing host is gated; no point retrying others.
                    break

            await browser.close()
    except Exception as e:
        print(f"  CTgoodjobs scraper error: {e}")

    if blocked:
        print("  CTgoodjobs: BLOCKED — jobs.ctgoodjobs.hk serves an interactive "
              "human-verification CAPTCHA on all listing pages. Returning [].")
    print(f"  CTgoodjobs total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
