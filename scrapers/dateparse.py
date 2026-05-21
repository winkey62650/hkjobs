"""
日期归一化工具
把各平台五花八门的「发布时间」字符串解析成真实日期 (datetime.date)。
解析失败返回 None。
"""
import re
from datetime import datetime, timedelta, date

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_posted(raw: str, anchor: date = None):
    """
    raw    : 平台显示的原始时间字符串，如 "3 days ago" / "今天" / "2024-05-18"
    anchor : 抓取当天的日期（相对时间的基准），默认今天
    返回   : datetime.date 或 None
    """
    if not raw:
        return None
    if anchor is None:
        anchor = datetime.utcnow().date()

    s = str(raw).strip().lower()
    if not s:
        return None

    # ── 「今天 / 刚刚 / just posted」类 → anchor ──────────────────────────────
    today_words = ["just posted", "just now", "today", "active today",
                   "今天", "今日", "刚刚", "剛剛", "newly posted", "new"]
    if any(w in s for w in today_words):
        return anchor

    # ── 「小时 / 分钟前」→ 仍算今天 ───────────────────────────────────────────
    if re.search(r"\d+\s*(hour|hr|minute|min|小时|小時|分鐘|分钟)", s):
        return anchor

    # ── 「昨天 / yesterday」→ anchor-1 ───────────────────────────────────────
    if "yesterday" in s or "昨天" in s or "昨日" in s:
        return anchor - timedelta(days=1)

    # ── 「X 天前 / X days ago」 ──────────────────────────────────────────────
    m = re.search(r"(\d+)\+?\s*(?:(?:days?|d)\b|天|日)", s)
    if m:
        return anchor - timedelta(days=int(m.group(1)))

    # ── 「X 周前 / X weeks ago」 ─────────────────────────────────────────────
    m = re.search(r"(\d+)\+?\s*(week|weeks|w|周|週|星期)", s)
    if m:
        return anchor - timedelta(weeks=int(m.group(1)))

    # ── 「X 月前 / X months ago」 ────────────────────────────────────────────
    m = re.search(r"(\d+)\+?\s*(month|months|個月|个月|月)", s)
    if m:
        return anchor - timedelta(days=30 * int(m.group(1)))

    # ── 「30+ days」单独的 30+ ───────────────────────────────────────────────
    if "30+" in s:
        return anchor - timedelta(days=30)

    # ── 绝对日期：2024-05-18 / 2024/05/18 ───────────────────────────────────
    m = re.search(r"(20\d\d)[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # ── 绝对日期：18-05-2024 / 18/05/2024 (日在前) ──────────────────────────
    m = re.search(r"(\d{1,2})[-/.](\d{1,2})[-/.](20\d\d)", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # ── 绝对日期：18 May 2024 / May 18, 2024 ────────────────────────────────
    m = re.search(r"(\d{1,2})\s*([a-z]{3,9})\s*,?\s*(20\d\d)", s)
    if m:
        mon = MONTHS.get(m.group(2)[:3])
        if mon:
            try:
                return date(int(m.group(3)), mon, int(m.group(1)))
            except ValueError:
                pass
    m = re.search(r"([a-z]{3,9})\s*(\d{1,2})\s*,?\s*(20\d\d)", s)
    if m:
        mon = MONTHS.get(m.group(1)[:3])
        if mon:
            try:
                return date(int(m.group(3)), mon, int(m.group(2)))
            except ValueError:
                pass

    return None


def days_ago(d: date, anchor: date = None) -> int:
    """返回 d 距今多少天（用于筛选）。"""
    if anchor is None:
        anchor = datetime.utcnow().date()
    return (anchor - d).days


if __name__ == "__main__":
    tests = ["Just posted", "3 days ago", "Posted 5 days ago", "30+ days ago",
             "今天", "昨天", "2天前", "1 week ago", "2024-05-18", "18/05/2024",
             "18 May 2024", "May 3, 2024", "5 hours ago", "1個月前", ""]
    for t in tests:
        print(f"{t!r:24} -> {parse_posted(t)}")
