#!/usr/bin/env python3
"""
每天两次：把「秒投」运行状态发到 Telegram。
检查项：职位数据量、数据新鲜度、近 13 小时爬虫运行成败。
环境变量：TG_BOT_TOKEN / TG_CHAT_ID / GH_TOKEN
"""
import os, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

HKT  = timezone(timedelta(hours=8))
REPO = "winkey62650/hkjobs"

TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT  = os.environ.get("TG_CHAT_ID", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")


def fmt(dt):
    return dt.astimezone(HKT).strftime("%Y-%m-%d %H:%M")


def get_json(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


# ── 1) 数据量 + 新鲜度 ───────────────────────────────────────────────────────
total, latest = 0, None
try:
    data = json.load(open("data/jobs.json", encoding="utf-8"))
    total = len(data)
    tss = [j.get("scraped_at", "") for j in data if j.get("scraped_at")]
    if tss:
        latest = datetime.strptime(max(tss), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
except Exception as ex:
    print("读取 jobs.json 失败:", ex)

# ── 2) 近 13 小时爬虫运行成败 ─────────────────────────────────────────────────
ok = fail = 0
try:
    runs = get_json(
        "https://api.github.com/repos/%s/actions/workflows/"
        "daily-scrape.yml/runs?per_page=25" % REPO, GH_TOKEN)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=13)
    for run in runs.get("workflow_runs", []):
        created = datetime.strptime(run["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        if created < cutoff:
            continue
        c = run.get("conclusion")
        if c == "success":
            ok += 1
        elif c == "failure":
            fail += 1
except Exception as ex:
    print("查询 Actions 运行失败:", ex)

# ── 3) 组装消息 ──────────────────────────────────────────────────────────────
now = datetime.now(HKT)
lines = ["📊 秒投 · 运行状态", "🕐 " + now.strftime("%m-%d %H:%M") + " HKT", ""]
lines.append("职位数据：%d 个" % total)

if latest:
    age_h = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    lines.append("最近更新：" + fmt(latest) + " HKT")
    if age_h <= 3:
        lines.append("🟢 数据更新正常")
    else:
        lines.append("🔴 数据已 %d 小时未更新，请检查！" % int(age_h))
else:
    lines.append("🔴 读不到数据更新时间")

lines.append("")
lines.append("近 13 小时爬虫：✅ %d 次　❌ %d 次" % (ok, fail))
if fail > 0:
    lines.append("⚠️ 有失败运行，建议查看 GitHub Actions")
elif ok == 0:
    lines.append("⚠️ 这段时间没有成功运行，请检查定时任务")

lines.append("")
lines.append("地图：https://hkjobs.vercel.app")
msg = "\n".join(lines)

# ── 4) 发送 Telegram ─────────────────────────────────────────────────────────
if not TG_TOKEN or not TG_CHAT:
    print("缺少 TG_BOT_TOKEN / TG_CHAT_ID，无法发送")
    raise SystemExit(1)

body = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg}).encode()
req = urllib.request.Request(
    "https://api.telegram.org/bot%s/sendMessage" % TG_TOKEN, data=body)
with urllib.request.urlopen(req, timeout=25) as r:
    res = json.load(r)
print("Telegram 发送:", "成功" if res.get("ok") else res)
