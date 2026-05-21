#!/usr/bin/env python3
"""
Multi-platform HK Job Scraper — orchestrator
- 自动发现 scrapers/ 目录下所有带 run() 的爬虫模块
- 并发抓取，按 URL 去重
- 与 data/jobs.json 的历史数据合并（保留全部历史）
- 为每条岗位计算 posted_date（真实发布日期估算）

用法: python3 run_all.py [max_pages]
"""
import asyncio, json, sys, importlib, traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta, date

HKT = timezone(timedelta(hours=8))   # 香港时间 UTC+8

ROOT      = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scrapers.dateparse import parse_posted   # noqa: E402

DATA_DIR  = ROOT / "data"
OUT_FILE  = DATA_DIR / "jobs.json"
MAX_PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 2

# dateparse / __init__ / jd_detail 不是爬虫，跳过
SKIP_MODULES = {"__init__", "dateparse", "jd_detail"}

# ── 完整 JD 抓取设置 ──────────────────────────────────────────────────────────
JD_SOURCES = {"JobsDB", "Recruit", "GovHK"}   # 详情页可抓的平台
JD_CAP     = 300                              # 每轮最多抓多少条（其余下轮再抓）
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def discover_scrapers():
    """返回 [(module_name, run_coro_func), ...]"""
    found = []
    for f in sorted((ROOT / "scrapers").glob("*.py")):
        name = f.stem
        if name in SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"scrapers.{name}")
        except Exception as ex:
            print(f"  ⚠️  无法导入 scrapers/{name}.py: {ex}")
            continue
        if hasattr(mod, "run") and asyncio.iscoroutinefunction(mod.run):
            found.append((name, mod.run))
        else:
            print(f"  ℹ️  scrapers/{name}.py 没有 async run()，跳过")
    return found


async def safe_run(name, run_func):
    """跑单个爬虫，永不抛异常。"""
    try:
        jobs = await run_func(max_pages=MAX_PAGES)
        return name, jobs or []
    except Exception as ex:
        print(f"  ⚠️  {name} 抓取失败: {ex}")
        traceback.print_exc()
        return name, []


async def fetch_full_jds(jobs, today_s):
    """访问详情页抓取完整 JD；每轮限量，只抓没抓过的（jd_fetched 标记）。"""
    from scrapers.jd_detail import fetch_jd
    from playwright.async_api import async_playwright

    todo = [j for j in jobs
            if j.get("source") in JD_SOURCES
            and not j.get("full_jd") and not j.get("jd_fetched")]
    if not todo:
        print("[run_all] 完整 JD：无待抓条目")
        return
    batch = todo[:JD_CAP]
    print(f"[run_all] 抓取完整 JD：本轮 {len(batch)} 条 / 待抓 {len(todo)} 条…")

    N = 4
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent=UA)
            pages = [await ctx.new_page() for _ in range(N)]

            async def worker(page, items):
                for j in items:
                    try:
                        jd = await fetch_jd(page, j["url"])
                    except Exception:
                        jd = ""
                    if jd:
                        j["full_jd"] = jd
                    j["jd_fetched"] = today_s   # 标记已尝试，避免下轮重复

            await asyncio.gather(*(worker(pages[i], batch[i::N]) for i in range(N)))
            await browser.close()
    except Exception as ex:
        print(f"[run_all] ⚠️  完整 JD 抓取异常: {ex}")
        return
    got = sum(1 for j in batch if j.get("full_jd"))
    print(f"[run_all] ✅ 完整 JD：成功 {got}/{len(batch)} 条")


async def main():
    DATA_DIR.mkdir(exist_ok=True)
    today    = datetime.now(HKT).date()                # 香港日期
    today_s  = today.isoformat()
    ts       = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── 载入历史 ───────────────────────────────────────────────────────────
    history = {}
    if OUT_FILE.exists():
        try:
            for j in json.loads(OUT_FILE.read_text(encoding="utf-8")):
                u = j.get("url", "")
                if u:
                    history[u] = j
            print(f"[run_all] 载入历史数据 {len(history)} 条")
        except Exception as ex:
            print(f"[run_all] ⚠️  历史数据读取失败，忽略: {ex}")

    # ── 发现并运行爬虫 ─────────────────────────────────────────────────────
    scrapers = discover_scrapers()
    print(f"[run_all] 发现 {len(scrapers)} 个爬虫: "
          f"{', '.join(n for n, _ in scrapers)}")
    print(f"[run_all] 开始抓取 (max_pages={MAX_PAGES})…\n")

    results = await asyncio.gather(*(safe_run(n, f) for n, f in scrapers))

    scraped = []
    for name, jobs in results:
        src = jobs[0].get("source", name) if jobs else name
        print(f"  ✅ {name}: {len(jobs)} 条")
        scraped.extend(jobs)

    # ── 合并历史 + 新数据 ──────────────────────────────────────────────────
    fresh, updated = 0, 0
    for j in scraped:
        u = j.get("url", "")
        if not u:
            continue
        pd = parse_posted(j.get("posted", ""), anchor=today)
        j["posted_date"] = pd.isoformat() if pd else None
        j["last_seen"]   = today_s
        j["scraped_at"]  = ts
        if u in history:
            old = history[u]
            j["first_seen"]    = old.get("first_seen", today_s)
            j["first_seen_ts"] = old.get("first_seen_ts") or \
                                 (j["first_seen"] + "T00:00:00Z")
            # 保留首次解析到的发布日期（更接近真实发布日）
            if old.get("posted_date") and not j["posted_date"]:
                j["posted_date"] = old["posted_date"]
            updated += 1
        else:
            j["first_seen"]    = today_s
            j["first_seen_ts"] = ts          # 精确到分钟的首次发现时间
            fresh += 1
        history[u] = j

    # ── effective_date：用于地图按日期筛选 ────────────────────────────────
    for j in history.values():
        if not j.get("first_seen"):
            j["first_seen"] = today_s
        if not j.get("first_seen_ts"):
            j["first_seen_ts"] = j["first_seen"] + "T00:00:00Z"
        j["effective_date"] = j.get("posted_date") or j.get("first_seen")

    merged = list(history.values())

    # ── 抓取完整 JD（限量；配合历史，只抓没抓过的）────────────────────────
    await fetch_full_jds(merged, today_s)

    OUT_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[run_all] ✅ 本轮抓取 {len(scraped)} 条 "
          f"(新增 {fresh} / 更新 {updated})")
    print(f"[run_all] ✅ 数据库累计 {len(merged)} 条 → {OUT_FILE}")
    return merged


if __name__ == "__main__":
    asyncio.run(main())
