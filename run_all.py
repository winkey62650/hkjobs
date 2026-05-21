#!/usr/bin/env python3
"""
Multi-platform HK Job Scraper
Runs JobsDB + Indeed HK scrapers concurrently and merges into data/jobs.json
"""
import asyncio, json, sys
from pathlib import Path
from datetime import datetime, timezone

# ── ensure scrapers package is importable ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from scrapers import jobsdb, indeed_hk

DATA_DIR  = Path(__file__).parent / "data"
OUT_FILE  = DATA_DIR / "jobs.json"
MAX_PAGES = int(sys.argv[1]) if len(sys.argv) > 1 else 2


async def main():
    DATA_DIR.mkdir(exist_ok=True)
    print(f"[run_all] Starting scrapers (max_pages={MAX_PAGES})…")

    # Run both scrapers concurrently
    results = await asyncio.gather(
        jobsdb.run(max_pages=MAX_PAGES),
        indeed_hk.run(max_pages=MAX_PAGES),
        return_exceptions=True,
    )

    all_jobs = []
    names    = ["JobsDB", "Indeed"]
    for name, r in zip(names, results):
        if isinstance(r, Exception):
            print(f"  ⚠️  {name} failed: {r}")
        else:
            print(f"  ✅ {name}: {len(r)} jobs")
            all_jobs.extend(r)

    # Deduplicate by URL
    seen, deduped = set(), []
    for j in all_jobs:
        u = j.get("url", "")
        if u and u not in seen:
            seen.add(u)
            deduped.append(j)

    # Stamp with scrape time
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for j in deduped:
        j["scraped_at"] = ts

    OUT_FILE.write_text(
        json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[run_all] ✅ {len(deduped)} unique jobs saved → {OUT_FILE}")
    return deduped


if __name__ == "__main__":
    asyncio.run(main())
