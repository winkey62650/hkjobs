"""JobMarket 求職廣場 HK scraper"""
import asyncio, re
from playwright.async_api import async_playwright

BASE   = "https://www.jobmarket.com.hk"
SOURCE = "JobMarket"
# (keyword, Chinese category label) -- site is bilingual, English keywords work
GROUPS = [
    ("assistant",            "助理"),
    ("operations",           "运营"),
    ("administration",       "行政"),
    ("coordinator",          "统筹"),
    ("content",              "内容"),
    ("copywriter",           "文案"),
    ("editor",               "编辑"),
    ("PR",                   "公关PR"),
    ("research",             "研究"),
    ("management trainee",   "管培生"),
    ("project",              "项目"),
    ("marketing",            "市场"),
    ("teacher",              "英语教学"),
    ("paralegal",            "法律辅助"),
    ("translator",           "翻译"),
]
MAX_PAGES = 2


def _clean(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


async def _text(node, sel):
    try:
        el = await node.query_selector(sel)
        if el:
            return _clean(await el.inner_text())
    except Exception:
        pass
    return ""


async def scrape_page(page, kw, pg):
    """Load the JobList iframe-page directly; it renders job cards via AJAX.

    Card rendering can be slow / intermittently flaky, so retry a couple times.
    """
    from urllib.parse import quote
    url = f"{BASE}/Job/JobList?Searchtext={quote(kw)}&Page={pg}"
    jobs = []
    cards = []
    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            continue
        try:
            await page.wait_for_selector("li[data-jobid]", timeout=20000)
        except Exception:
            pass
        await page.wait_for_timeout(2500)
        try:
            cards = await page.query_selector_all("li[data-jobid]")
        except Exception:
            cards = []
        if cards:
            break

    for c in cards:
        try:
            jid = (await c.get_attribute("data-jobid") or "").strip()
            if not jid:
                continue
            title = await _text(c, "h3 a") or await _text(c, "h3")
            if not title:
                continue
            company = await _text(c, ".company-name a") or await _text(c, ".company-name")
            location = await _text(c, ".company-addr")
            if location.lower() == "loading":
                location = ""
            snippet = await _text(c, ".job-list-summary-text")
            posted = await _text(c, ".post-date")
            # strip the leading "Post Date" / label noise
            posted = re.sub(r"^(post date|刊登日期|刊登日)\s*", "", posted, flags=re.I).strip()
            # salary sometimes present in summary/detail text
            salary = ""
            m = re.search(r"(HK\$|\$)\s?[\d,]+(\s?-\s?[\d,]+)?", snippet)
            if m:
                salary = m.group(0)
            jobs.append({
                "title":    title,
                "url":      f"{BASE}/Job/?Jobid={jid}",
                "company":  company,
                "location": location,
                "salary":   salary,
                "snippet":  snippet,
                "posted":   posted,
                "source":   SOURCE,
                "label":    "",
            })
        except Exception:
            continue
    return jobs


async def run(max_pages=MAX_PAGES):
    all_jobs, seen = [], set()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                locale="zh-HK", viewport={"width": 1280, "height": 900})
            page = await ctx.new_page()
            for kw, label in GROUPS:
                print(f"  [JobMarket/{label}] {kw}")
                for pg in range(1, max_pages + 1):
                    try:
                        jobs = await scrape_page(page, kw, pg)
                    except Exception as e:
                        print(f"    p{pg}: error {e}")
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
            await browser.close()
    except Exception as e:
        print(f"  JobMarket fatal: {e}")
        return all_jobs
    print(f"  JobMarket total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
