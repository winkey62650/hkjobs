"""
完整 JD 抓取 — 访问职位详情页，提取完整的职位描述。
策略：JSON-LD JobPosting.description 优先（标准化、最可靠），
否则在一组候选容器里取文字最长的。尽力而为，失败返回 ''。
"""
import json, re, html

CANDIDATE_SELECTORS = [
    '[data-automation="jobAdDetails"]',          # JobsDB / SEEK
    '[data-automation="jobDescription"]',
    '[class*="jobDescription"]', '[class*="job-description"]',
    '[id*="job-description"]', '[id*="jobDescription"]',
    '[class*="JobDescription"]', '[class*="job-detail"]',
    '[class*="jobDetail"]', '[class*="job-content"]',
    '[class*="jobAd"]', '.description', '#description',
    '[id*="deltab"]', '[id*="Detail"]',          # GovHK 文本页
    'article', 'main', 'td',
]


def _strip_html(s):
    s = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', s or '')
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)
    s = re.sub(r'(?i)</(p|div|li|h[1-6]|tr)>', '\n', s)
    s = re.sub(r'(?i)<li[^>]*>', '• ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s


def _clean(t):
    t = html.unescape(t or '')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r' *\n *', '\n', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()[:6000]


async def fetch_jd(page, url):
    """访问详情页，返回完整 JD 文本；失败或被拦截返回 ''。"""
    if not url or not url.startswith("http"):
        return ""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        return ""
    await page.wait_for_timeout(2200)   # 等 JS 渲染

    # 1) JSON-LD JobPosting.description —— 标准化，最可靠
    try:
        for s in await page.query_selector_all('script[type="application/ld+json"]'):
            try:
                data = json.loads(await s.inner_text())
            except Exception:
                continue
            items = data if isinstance(data, list) else [data]
            # 有的站点把多个对象塞进 @graph
            for it in list(items):
                if isinstance(it, dict) and isinstance(it.get("@graph"), list):
                    items += it["@graph"]
            for obj in items:
                if not isinstance(obj, dict):
                    continue
                t = obj.get("@type", "")
                types = t if isinstance(t, list) else [t]
                if "JobPosting" in types and obj.get("description"):
                    txt = _clean(_strip_html(obj["description"]))
                    if len(txt) > 120:
                        return txt
    except Exception:
        pass

    # 2) 候选容器 —— 取文字最长的那个
    best = ""
    for sel in CANDIDATE_SELECTORS:
        try:
            for el in await page.query_selector_all(sel):
                try:
                    txt = (await el.inner_text()).strip()
                except Exception:
                    continue
                if len(txt) > len(best):
                    best = txt
        except Exception:
            pass
        if len(best) > 600:
            break
    return _clean(best)


if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright

    TESTS = [
        ("JobsDB",    "https://hk.jobsdb.com/job/92259486"),
        ("Recruit",   "https://www.recruit.com.hk/job-detail/建業建築工程公司/機場文員/L059988237"),
        ("JobMarket", "https://www.jobmarket.com.hk/Job/?Jobid=2366965"),
        ("GovHK",     "https://csboa2.csb.gov.hk/csboa/jve/JVE_003_text.action?jobid=49742&languageType=2"),
    ]

    async def main():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36")
            page = await ctx.new_page()
            for name, url in TESTS:
                jd = await fetch_jd(page, url)
                preview = jd[:160].replace("\n", " ⏎ ")
                print(f"\n[{name}] {len(jd)} chars")
                print(f"  {preview}")
            await browser.close()

    asyncio.run(main())
