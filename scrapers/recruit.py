"""Recruit.com.hk scraper"""
import asyncio
from playwright.async_api import async_playwright

BASE   = "https://www.recruit.com.hk"
SEARCH = BASE + "/jobseeker/JobSearchResult.aspx?searchPath=K&keyword={kw}"
GROUPS = [
    ("assistant",          "助理"),
    ("operations",         "运营"),
    ("administration",     "行政"),
    ("coordinator",        "统筹"),
    ("content",            "内容"),
    ("copywriter",         "文案"),
    ("editor",             "编辑"),
    ("public relations",   "公关PR"),
    ("research",           "研究"),
    ("management trainee", "管培生"),
    ("programme officer",  "项目"),
    ("marketing",          "市场"),
    ("english teacher",    "英语教学"),
    ("paralegal",          "法律辅助"),
    ("translator",         "翻译"),
]
MAX_PAGES = 2
SOURCE    = "Recruit"


async def _txt(el):
    try:
        return (await el.inner_text()).strip()
    except Exception:
        return ""


async def scrape_rows(page):
    """Parse all tr.JobGrid cards currently in the DOM."""
    jobs = []
    for row in await page.query_selector_all("tr.JobGrid"):
        try:
            a = await row.query_selector("a.title")
            if not a:
                continue
            title = (await a.inner_text()).strip()
            href = await a.get_attribute("href") or ""
            if not href:
                continue
            url = href if href.startswith("http") else BASE + href.split("?")[0]

            comp = await row.query_selector("a.company")
            company = (await _txt(comp)) if comp else ""

            pd = await row.query_selector(".post-date, .post-date-col")
            posted = (await _txt(pd)) if pd else ""

            sc = await row.query_selector(".salary-col")
            salary = (await _txt(sc)) if sc else ""
            if salary in ("--", "-", "N/A"):
                salary = ""

            jobs.append({
                "title": title,
                "url": url,
                "company": company,
                "location": "",
                "salary": salary,
                "snippet": "",
                "posted": posted,
                "source": SOURCE,
                "label": "",
            })
        except Exception:
            continue
    return jobs


async def scrape_keyword(page, kw, max_pages):
    """Search one keyword, paginate via the ASP.NET 'Next' postback."""
    out = []
    try:
        await page.goto(SEARCH.format(kw=kw.replace(" ", "+")),
                        wait_until="networkidle", timeout=60000)
    except Exception:
        return out
    try:
        await page.wait_for_selector("tr.JobGrid", timeout=15000)
    except Exception:
        return out

    for pg in range(1, max_pages + 1):
        rows = await scrape_rows(page)
        out.extend(rows)
        if pg >= max_pages:
            break
        # advance to next page
        try:
            nxt = await page.query_selector("a:has-text('Next')")
            if not nxt:
                break
            first = await page.eval_on_selector(
                "tr.JobGrid a.title", "e=>e.innerText")
            await nxt.click()
            await page.wait_for_load_state("networkidle", timeout=45000)
            await page.wait_for_function(
                "(b)=>{const e=document.querySelector('tr.JobGrid a.title');"
                "return e && e.innerText!==b;}",
                arg=first, timeout=20000)
        except Exception:
            break
    return out


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
                print(f"  [Recruit/{label}] {kw}")
                try:
                    jobs = await scrape_keyword(page, kw, max_pages)
                except Exception:
                    jobs = []
                new = 0
                for j in jobs:
                    u = j.get("url", "")
                    if u and u not in seen:
                        seen.add(u)
                        j["label"] = label
                        all_jobs.append(j)
                        new += 1
                print(f"    +{new}")
            await browser.close()
    except Exception as e:
        print(f"  Recruit error: {e}")
        return all_jobs
    print(f"  Recruit total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
