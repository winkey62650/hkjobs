"""Indeed HK scraper"""
import asyncio, re
from playwright.async_api import async_playwright

BASE = "https://hk.indeed.com"
QUERIES = [
    ("assistant",           "助理"),
    ("operations",          "运营"),
    ("administrative",      "行政"),
    ("coordinator",         "统筹"),
    ("content writer",      "内容"),
    ("copywriter",          "文案"),
    ("editor",              "编辑"),
    ("public relations",    "公关PR"),
    ("research",            "研究"),
    ("management trainee",  "管培生"),
    ("programme officer",   "项目"),
    ("marketing",           "市场"),
    ("english teacher",     "英语教学"),
    ("paralegal",           "法律辅助"),
    ("translator",          "翻译"),
]
MAX_PAGES = 2   # Indeed每页~15条，start=0,15,30...
SOURCE    = "Indeed"

async def scrape_page(page, query, start):
    q_enc = query.replace(" ", "+")
    url = f"{BASE}/jobs?q={q_enc}&l=Hong+Kong&start={start}"
    await page.goto(url, wait_until="domcontentloaded", timeout=40000)
    try:
        await page.wait_for_selector('[class*="job_seen_beacon"]', timeout=12000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)

    jobs = []
    cards = await page.query_selector_all('[class*="job_seen_beacon"]')
    for card in cards:
        j = {}
        # 标题 + 链接
        t = await card.query_selector('[data-testid="jobTitle"] a, h2 a')
        if not t:
            continue
        j["title"] = (await t.inner_text()).strip()
        href = await t.get_attribute("href") or ""
        if href.startswith("/"):
            href = BASE + href
        # 去掉追踪参数，保留 jk=
        jk_match = re.search(r'jk=([a-f0-9]+)', href)
        j["url"] = f"{BASE}/rc/clk?jk={jk_match.group(1)}" if jk_match else href

        # 公司
        co = await card.query_selector('[data-testid="company-name"]')
        j["company"] = (await co.inner_text()).strip() if co else ""

        # 地点
        loc = await card.query_selector('[data-testid="text-location"]')
        j["location"] = (await loc.inner_text()).strip() if loc else ""

        # 薪资（不是每个都有）
        sal = await card.query_selector('[data-testid="attribute_snippet_testid"], .salary-snippet-container')
        j["salary"] = (await sal.inner_text()).strip() if sal else ""

        # 描述摘要
        desc = await card.query_selector('[data-testid="job-snippet"] ul, .job-snippet')
        if desc:
            items = await desc.query_selector_all("li")
            bullets = [((await i.inner_text()).strip()) for i in items[:3]]
            j["snippet"] = " · ".join(bullets)
        else:
            j["snippet"] = ""

        # 发布时间
        date = await card.query_selector('[data-testid="myJobsStateDate"], .date')
        j["posted"] = (await date.inner_text()).strip() if date else ""

        j["source"] = SOURCE
        jobs.append(j)
    return jobs


async def run(max_pages=MAX_PAGES):
    all_jobs, seen = [], set()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            locale="en-HK", viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()

        for query, label in QUERIES:
            print(f"  [Indeed/{label}] {query}")
            for pg in range(max_pages):
                start = pg * 15
                jobs = await scrape_page(page, query, start)
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
                print(f"    p{pg+1}: +{new}")
                if new == 0:
                    break
        await browser.close()
    print(f"  Indeed total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run(max_pages=1))
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
