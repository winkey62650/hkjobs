"""NGO (HKCSS x CTgoodjobs) HK scraper.

The HK NGO recruitment site (formerly referenced as ngogoodjobs) is the
HKCSS x CTgoodjobs NGO portal at https://ngo.ctgoodjobs.hk.

The job *search* listing host (jobs.ctgoodjobs.hk) is protected by a
hard bot wall (HTTP 405 + human verification). The ngo.ctgoodjobs.hk
host itself is reachable and exposes per-organisation job openings, so
this scraper walks the organisation directory and collects every job
opening card it finds, then assigns a Chinese category label by
keyword-matching the job title.
"""
import asyncio
from playwright.async_api import async_playwright

BASE   = "https://ngo.ctgoodjobs.hk"
SOURCE = "NGO"
MAX_PAGES = 2

# label -> keywords matched (case-insensitive) against the job title
CATEGORIES = [
    ("助理",    ["assistant", "助理"]),
    ("运营",    ["operations", "operation", "運營", "营运", "營運"]),
    ("行政",    ["administration", "administrative", "admin", "clerk", "行政", "文員"]),
    ("统筹",    ["coordinator", "coordination", "統籌", "统筹"]),
    ("内容",    ["content", "內容", "内容"]),
    ("文案",    ["copywriter", "copywriting", "文案"]),
    ("编辑",    ["editor", "editorial", "編輯", "编辑"]),
    ("公关PR",  ["communications", "communication", "public relations", "公關", "公关"]),
    ("研究",    ["research", "researcher", "研究"]),
    ("管培生",  ["trainee", "graduate trainee", "management trainee", "管培"]),
    ("项目",    ["project", "programme", "program", "項目", "项目"]),
    ("市场",    ["marketing", "市場", "市场"]),
    ("英语教学", ["teacher", "teaching", "tutor", "教學", "教学", "導師"]),
    ("法律辅助", ["legal", "paralegal", "law", "法律"]),
    ("翻译",    ["translator", "translation", "interpreter", "翻譯", "翻译"]),
]
DEFAULT_LABEL = "项目"


def classify(title):
    """Assign a Chinese category label by keyword-matching the title."""
    t = (title or "").lower()
    for label, keywords in CATEGORIES:
        for kw in keywords:
            if kw.lower() in t:
                return label
    return DEFAULT_LABEL


async def _text(node, sel):
    try:
        el = await node.query_selector(sel)
        if el:
            return (await el.inner_text()).strip()
    except Exception:
        pass
    return ""


async def _collect_cards(page):
    """Extract job-opening cards from the currently loaded page."""
    jobs = []
    try:
        cards = await page.query_selector_all("div.job")
    except Exception:
        return jobs
    for card in cards:
        try:
            link = await card.query_selector("a.a-overlay, a[href*='/job/']")
            if not link:
                continue
            href = await link.get_attribute("href") or ""
            if not href or "/job/" not in href:
                continue
            url = href if href.startswith("http") else BASE + href
            url = url.split("?")[0]
            title = await _text(card, ".job__title")
            if not title:
                continue
            jobs.append({
                "title":    title,
                "url":      url,
                "company":  await _text(card, ".job__company"),
                "location": "",
                "salary":   "",
                "snippet":  "",
                "posted":   await _text(card, ".job__postdate"),
                "source":   SOURCE,
                "label":    classify(title),
            })
        except Exception:
            continue
    return jobs


async def _org_links(page):
    """Distinct organisation profile URLs on the current directory page."""
    try:
        return await page.eval_on_selector_all(
            "a",
            "els => [...new Set(els.map(e => e.href)"
            ".filter(h => h && h.includes('/organisation/00')))]",
        )
    except Exception:
        return []


async def run(max_pages=MAX_PAGES):
    """Scrape NGO job openings; returns a list of job dicts. Never raises."""
    all_jobs, seen = [], set()
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36",
                locale="zh-HK",
                viewport={"width": 1280, "height": 900},
            )
            page = await ctx.new_page()

            org_urls = []
            for pg in range(1, max_pages + 1):
                try:
                    url = f"{BASE}/organisation" if pg == 1 \
                        else f"{BASE}/organisation?page={pg}"
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    links = await _org_links(page)
                except Exception as e:
                    print(f"  [NGO] org directory p{pg} failed: {e}")
                    break
                new = [u for u in links if u not in org_urls]
                org_urls.extend(new)
                print(f"  [NGO] org directory p{pg}: +{len(new)} orgs")
                if not new:
                    break

            print(f"  [NGO] scanning {len(org_urls)} organisations")
            for i, org_url in enumerate(org_urls, 1):
                try:
                    await page.goto(org_url, wait_until="networkidle",
                                    timeout=60000)
                    jobs = await _collect_cards(page)
                except Exception as e:
                    print(f"  [NGO] org {i} failed: {e}")
                    continue
                added = 0
                for j in jobs:
                    u = j["url"]
                    if u and u not in seen:
                        seen.add(u)
                        all_jobs.append(j)
                        added += 1
                if added:
                    print(f"  [NGO] org {i}/{len(org_urls)}: +{added}")

            await browser.close()
    except Exception as e:
        print(f"  [NGO] fatal: {e}")
        return all_jobs

    print(f"  NGO total: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    import json
    jobs = asyncio.run(run())
    print(json.dumps(jobs[:2], ensure_ascii=False, indent=2))
