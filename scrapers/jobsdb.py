"""JobsDB HK scraper"""
import asyncio, re
from playwright.async_api import async_playwright

BASE   = "https://hk.jobsdb.com"
GROUPS = [
    ("assistant",            "助理"),
    ("operations",           "运营"),
    ("administrative",       "行政"),
    ("coordinator",          "统筹"),
    ("content",              "内容"),
    ("copywriter",           "文案"),
    ("editor",               "编辑"),
    ("public-relations",     "公关PR"),
    ("research",             "研究"),
    ("management-trainee",   "管培生"),
    ("programme-officer",    "项目"),
    ("marketing",            "市场"),
    ("esl-teacher",          "英语教学"),
    ("paralegal",            "法律辅助"),
    ("translator",           "翻译"),
]
MAX_PAGES = 2
SOURCE    = "JobsDB"

async def scrape_page(page, kw, pg):
    url = f"{BASE}/{kw}-jobs?page={pg}"
    await page.goto(url, wait_until="networkidle", timeout=60000)
    try:
        await page.wait_for_selector("article", timeout=15000)
    except Exception:
        pass
    jobs = []
    for art in await page.query_selector_all("article"):
        j = {}
        t = await art.query_selector('[data-automation="jobTitle"]')
        if not t:
            continue
        j["title"] = (await t.inner_text()).strip()
        href = await t.get_attribute("href") or ""
        j["url"] = href if href.startswith("http") else BASE + href.split("?")[0]
        for sel, key in [
            ('[data-automation="jobCompany"]', "company"),
            ('[data-automation="jobShortDescription"]', "snippet"),
            ('[data-automation="jobListingDate"]', "posted"),
        ]:
            el = await art.query_selector(sel)
            j[key] = (await el.inner_text()).strip() if el else ""
        locs, seen = [], set()
        for lel in await art.query_selector_all('[data-automation="jobCardLocation"]'):
            txt = (await lel.inner_text()).strip().strip(",")
            if txt and txt not in seen:
                seen.add(txt); locs.append(txt)
        j["location"] = " · ".join(locs[:2])
        sal = ""
        for el in await art.query_selector_all("span"):
            try:
                txt = (await el.inner_text()).strip()
                if "$" in txt and 3 < len(txt) < 60:
                    sal = txt; break
            except Exception:
                pass
        j["salary"] = sal
        j["source"] = SOURCE
        jobs.append(j)
    return jobs


async def run(max_pages=MAX_PAGES):
    all_jobs, seen = [], set()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="zh-HK", viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        for kw, label in GROUPS:
            print(f"  [JobsDB/{label}] {kw}")
            for pg in range(1, max_pages + 1):
                jobs = await scrape_page(page, kw, pg)
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
    print(f"  JobsDB total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
