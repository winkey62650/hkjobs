#!/usr/bin/env python3
"""
秒投 · 自动健康监控（QA 系统）
每 30 分钟体检一次：线上网页、API、数据新鲜度、爬虫运行。
只在「状态变化」时报警（正常→故障 🔴 / 故障→恢复 🟢），不刷屏。
状态存 data/health.json。
环境变量：TG_BOT_TOKEN / TG_CHAT_ID / GH_TOKEN
"""
import os, json, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone, timedelta

HKT       = timezone(timedelta(hours=8))
REPO      = "winkey62650/hkjobs"
SITE      = "https://hkjobs.vercel.app"
STATE_F   = "data/health.json"

TG_TOKEN  = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT   = os.environ.get("TG_CHAT_ID", "")
GH_TOKEN  = os.environ.get("GH_TOKEN", "")

# ── 阈值 ──────────────────────────────────────────────────────────────────────
DATA_MAX_AGE_H = 3      # 数据超过 3 小时没更新 → 故障
MIN_JOBS       = 200    # 职位总量低于此 → 故障（爬虫可能抓崩了）
HTTP_TIMEOUT   = 25


def now_hkt():
    return datetime.now(HKT).strftime("%m-%d %H:%M")


# ── 单项检查工具 ──────────────────────────────────────────────────────────────
def check_url(url):
    """返回 (ok, 说明)。2xx/3xx 视为通。"""
    try:
        req = urllib.request.Request(url, method="GET",
                                     headers={"User-Agent": "miaotou-healthcheck"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return (True, "HTTP %d" % r.status)
    except urllib.error.HTTPError as e:
        return (False, "HTTP %d" % e.code)
    except Exception as e:
        return (False, str(e)[:60])


def check_api():
    """POST /api/account 一个不存在的账号：返回 404 = API+数据库都活着。"""
    url  = SITE + "/api/account"
    body = json.dumps({"action": "load", "id": "__healthcheck__"}).encode()
    req  = urllib.request.Request(url, data=body, method="POST",
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return (True, "HTTP %d" % r.status)
    except urllib.error.HTTPError as e:
        # 404 = 账号不存在（预期）；其余 4xx 也算 API 活着
        if e.code in (400, 404):
            return (True, "HTTP %d（预期）" % e.code)
        return (False, "HTTP %d" % e.code)
    except Exception as e:
        return (False, str(e)[:60])


def check_data():
    """读本地 jobs.json：返回 (ok, 说明, total)。"""
    try:
        data = json.load(open("data/jobs.json", encoding="utf-8"))
        total = len(data)
        tss = [j.get("scraped_at", "") for j in data if j.get("scraped_at")]
        if not tss:
            return (False, "无更新时间戳", total)
        latest = datetime.strptime(max(tss), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
        if total < MIN_JOBS:
            return (False, "职位仅 %d 个（疑似爬虫异常）" % total, total)
        if age_h > DATA_MAX_AGE_H:
            return (False, "已 %.1f 小时未更新" % age_h, total)
        return (True, "%d 个职位 · %.1fh 前更新" % (total, age_h), total)
    except Exception as e:
        return (False, "读取失败：" + str(e)[:50], 0)


def check_scrape():
    """近 3 小时 daily-scrape 运行成败。"""
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/%s/actions/workflows/"
            "daily-scrape.yml/runs?per_page=20" % REPO)
        if GH_TOKEN:
            req.add_header("Authorization", "Bearer " + GH_TOKEN)
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            runs = json.load(r).get("workflow_runs", [])
        cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
        ok = fail = 0
        for run in runs:
            created = datetime.strptime(
                run["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if created < cutoff:
                continue
            c = run.get("conclusion")
            if c == "success":
                ok += 1
            elif c == "failure":
                fail += 1
        if ok == 0 and fail == 0:
            return (False, "近 3 小时无运行（定时任务可能停了）")
        if ok == 0:
            return (False, "近 3 小时 %d 次全部失败" % fail)
        return (True, "近 3 小时 ✅%d ❌%d" % (ok, fail))
    except Exception as e:
        return (False, "查询失败：" + str(e)[:50])


# ── 跑全部检查 ────────────────────────────────────────────────────────────────
checks = []

for label, path in [("首页", "/"), ("欢迎页", "/welcome.html"),
                     ("收藏页", "/saved.html"), ("简历页", "/resume.html")]:
    ok, msg = check_url(SITE + path)
    checks.append({"name": "网页·" + label, "ok": ok, "msg": msg})

ok, msg = check_api()
checks.append({"name": "API/数据库", "ok": ok, "msg": msg})

ok, msg, total = check_data()
checks.append({"name": "数据新鲜度", "ok": ok, "msg": msg})

ok, msg = check_scrape()
checks.append({"name": "爬虫运行", "ok": ok, "msg": msg})

failed   = [c for c in checks if not c["ok"]]
overall  = "down" if failed else "ok"
ts_iso   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── 读旧状态、对比 ────────────────────────────────────────────────────────────
prev = {}
try:
    prev = json.load(open(STATE_F, encoding="utf-8"))
except Exception:
    pass
prev_overall = prev.get("overall", "ok")

# ── 写新状态 ──────────────────────────────────────────────────────────────────
state = {
    "overall": overall,
    "checked_at": ts_iso,
    "since": ts_iso if overall != prev_overall else prev.get("since", ts_iso),
    "checks": checks,
}
os.makedirs("data", exist_ok=True)
with open(STATE_F, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("体检结果：%s（上次：%s）" % (overall, prev_overall))
for c in checks:
    print(("  ✅ " if c["ok"] else "  ❌ ") + c["name"] + "：" + c["msg"])


# ── 报警：仅状态变化时发 ──────────────────────────────────────────────────────
def send_tg(text):
    if not TG_TOKEN or not TG_CHAT:
        print("缺少 TG 配置，跳过发送")
        return
    body = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": text}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/sendMessage" % TG_TOKEN, data=body)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            print("Telegram:", "成功" if json.load(r).get("ok") else "失败")
    except Exception as e:
        print("Telegram 发送出错:", e)


if overall != prev_overall:
    if overall == "down":
        lines = ["🔴 秒投 · 健康检查报警", "🕐 " + now_hkt() + " HKT", ""]
        lines += ["❌ " + c["name"] + "：" + c["msg"] for c in failed]
        ok_items = [c for c in checks if c["ok"]]
        if ok_items:
            lines += ["", "其余正常：" + "、".join(c["name"] for c in ok_items)]
        lines += ["", "查看：https://github.com/%s/actions" % REPO]
    else:
        lines = ["🟢 秒投 · 已恢复正常", "🕐 " + now_hkt() + " HKT",
                 "", "全部 %d 项检查通过 ✅" % len(checks)]
    send_tg("\n".join(lines))
else:
    print("状态未变化，不发送通知。")
