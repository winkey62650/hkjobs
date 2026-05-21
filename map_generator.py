#!/usr/bin/env python3
"""
HK Jobs 地图生成器 — Multi-platform edition
读取 data/jobs.json，生成交互式香港地图 index.html
"""

import json, re, sys
from pathlib import Path
from datetime import datetime, timedelta

DATA_FILE   = Path(__file__).parent / "data" / "jobs.json"
OUTPUT_FILE = Path(__file__).parent / "index.html"

# ── 香港地点坐标字典 ─────────────────────────────────────────────────────────
HK_COORDS = {
    # 港岛
    "central and western": [22.2830, 114.1501, "中西区 Central & Western"],
    "central":             [22.2817, 114.1581, "中环 Central"],
    "sheung wan":          [22.2866, 114.1520, "上环 Sheung Wan"],
    "admiralty":           [22.2794, 114.1655, "金钟 Admiralty"],
    "wan chai":            [22.2783, 114.1747, "湾仔 Wan Chai"],
    "causeway bay":        [22.2804, 114.1839, "铜锣湾 Causeway Bay"],
    "happy valley":        [22.2692, 114.1836, "跑马地 Happy Valley"],
    "north point":         [22.2912, 114.1990, "北角 North Point"],
    "quarry bay":          [22.2877, 114.2090, "鲗鱼涌 Quarry Bay"],
    "tai koo":             [22.2843, 114.2162, "太古 Tai Koo"],
    "sai wan ho":          [22.2824, 114.2222, "西湾河 Sai Wan Ho"],
    "shau kei wan":        [22.2789, 114.2289, "筲箕湾 Shau Kei Wan"],
    "chai wan":            [22.2641, 114.2366, "柴湾 Chai Wan"],
    "aberdeen":            [22.2490, 114.1518, "香港仔 Aberdeen"],
    "wong chuk hang":      [22.2499, 114.1705, "黄竹坑 Wong Chuk Hang"],
    "ap lei chau":         [22.2425, 114.1553, "鸭脷洲 Ap Lei Chau"],
    "southern district":   [22.2465, 114.1601, "南区 Southern District"],
    "eastern district":    [22.2841, 114.2215, "东区 Eastern District"],
    "hong kong island":    [22.2780, 114.1747, "香港岛 HK Island"],
    "hong kong sar":       [22.3193, 114.1694, "香港 Hong Kong"],
    "hong kong":           [22.3193, 114.1694, "香港 Hong Kong"],
    # 九龙
    "tsim sha tsui":       [22.2988, 114.1724, "尖沙咀 Tsim Sha Tsui"],
    "yau ma tei":          [22.3127, 114.1700, "油麻地 Yau Ma Tei"],
    "mong kok":            [22.3193, 114.1694, "旺角 Mong Kok"],
    "yau tsim mong":       [22.3128, 114.1710, "油尖旺 Yau Tsim Mong"],
    "sham shui po":        [22.3307, 114.1623, "深水埗 Sham Shui Po"],
    "lai chi kok":         [22.3370, 114.1480, "荔枝角 Lai Chi Kok"],
    "cheung sha wan":      [22.3352, 114.1559, "长沙湾 Cheung Sha Wan"],
    "hung hom":            [22.3030, 114.1826, "红磡 Hung Hom"],
    "to kwa wan":          [22.3163, 114.1898, "土瓜湾 To Kwa Wan"],
    "kowloon city":        [22.3282, 114.1916, "九龙城 Kowloon City"],
    "kowloon bay":         [22.3230, 114.2139, "九龙湾 Kowloon Bay"],
    "ngau tau kok":        [22.3155, 114.2191, "牛头角 Ngau Tau Kok"],
    "kwun tong":           [22.3124, 114.2262, "观塘 Kwun Tong"],
    "lam tin":             [22.3085, 114.2346, "蓝田 Lam Tin"],
    "kai tak":             [22.3282, 114.2007, "启德 Kai Tak"],
    "kowloon":             [22.3193, 114.1694, "九龙 Kowloon"],
    # 新界
    "kwai chung":          [22.3590, 114.1285, "葵涌 Kwai Chung"],
    "kwai hing":           [22.3628, 114.1318, "葵兴 Kwai Hing"],
    "kwai fong":           [22.3571, 114.1246, "葵芳 Kwai Fong"],
    "kwai tsing":          [22.3590, 114.1285, "葵青 Kwai Tsing"],
    "tsuen wan":           [22.3718, 114.1138, "荃湾 Tsuen Wan"],
    "sha tin":             [22.3832, 114.1888, "沙田 Sha Tin"],
    "tai po":              [22.4513, 114.1645, "大埔 Tai Po"],
    "yuen long":           [22.4445, 114.0220, "元朗 Yuen Long"],
    "tuen mun":            [22.3916, 113.9769, "屯门 Tuen Mun"],
    "tseung kwan o":       [22.3077, 114.2595, "将军澳 Tseung Kwan O"],
    "sai kung":            [22.3813, 114.2709, "西贡 Sai Kung"],
    "clearwater bay":      [22.2960, 114.3002, "清水湾 Clearwater Bay"],
    "fanling":             [22.4921, 114.1390, "粉岭 Fanling"],
    "sheung shui":         [22.5013, 114.1278, "上水 Sheung Shui"],
    "tin shui wai":        [22.4498, 113.9969, "天水围 Tin Shui Wai"],
    "ma on shan":          [22.4261, 114.2317, "马鞍山 Ma On Shan"],
    "fo tan":              [22.3975, 114.1985, "火炭 Fo Tan"],
    "diamond hill":        [22.3396, 114.2100, "钻石山 Diamond Hill"],
    "wong tai sin":        [22.3416, 114.1932, "黄大仙 Wong Tai Sin"],
    "new territories":     [22.3832, 114.1888, "新界 New Territories"],
}

LABEL_COLORS = {
    "助理":    "#6366f1",
    "运营":    "#10b981",
    "行政":    "#f59e0b",
    "统筹":    "#ec4899",
    "内容":    "#8b5cf6",
    "文案":    "#e11d48",
    "编辑":    "#0891b2",
    "公关PR":  "#7c3aed",
    "研究":    "#15803d",
    "管培生":  "#dc2626",
    "项目":    "#0f766e",
    "市场":    "#9333ea",
    "英语教学":"#047857",
    "法律辅助":"#92400e",
    "翻译":    "#b45309",
}

SOURCE_COLORS = {
    "JobsDB":     "#e60028",
    "Indeed":     "#2164f3",
    "CTgoodjobs": "#f97316",
    "GovHK":      "#1e7d34",
    "NGO":        "#0d9488",
    "Recruit":    "#7c3aed",
    "JobMarket":  "#db2777",
}


def geocode(location: str):
    loc_lower = location.lower()
    for key, coords in HK_COORDS.items():
        if key in loc_lower:
            return coords
    first = loc_lower.split("·")[0].strip().split(",")[0].strip()
    for key, coords in HK_COORDS.items():
        if key in first or first in key:
            return coords
    return None


def parse_sal_num(s: str) -> float:
    s2 = s.upper().replace(",", "").replace("HK$", "").replace("$", "")
    nums = re.findall(r"\d+", s2)
    if not nums:
        return 0.0
    v = float(nums[0])
    return v * 1000 if "K" in s2 else v


def e(s: str) -> str:
    return (s.replace("\\", "\\\\").replace("`", "\\`")
             .replace("$", "\\$").replace("<", "&lt;").replace(">", "&gt;"))


# ── 读取数据 ──────────────────────────────────────────────────────────────────
data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
print(f"读取 {len(data)} 个职位")

# 来源统计
source_counts = {}
for j in data:
    s = j.get("source", "Unknown")
    source_counts[s] = source_counts.get(s, 0) + 1
for s, c in source_counts.items():
    print(f"  {s}: {c}")

# 按地点分组
loc_groups = {}
ungrouped  = []

for j in data:
    loc_raw = j.get("location", "").strip()
    coords  = geocode(loc_raw) if loc_raw else None
    if coords:
        key = coords[2]
        if key not in loc_groups:
            loc_groups[key] = {"lat": coords[0], "lng": coords[1],
                               "name": coords[2], "jobs": []}
        loc_groups[key]["jobs"].append(j)
    else:
        ungrouped.append(j)

print(f"已定位 {sum(len(g['jobs']) for g in loc_groups.values())} 个职位，"
      f"{len(ungrouped)} 个无法定位")

# 无法定位的岗位 → 收进「不限地区」桶，仍可在地图上点开浏览
if ungrouped:
    loc_groups["🌐 不限地区 All HK"] = {
        "lat": 22.165, "lng": 114.10,
        "name": "🌐 不限地区 All HK", "jobs": ungrouped,
    }

# ── 新增岗位检测（最近一小时内首次发现的岗位）────────────────────────────────
gen_dt      = datetime.utcnow()
gen_ts_iso  = gen_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
_new_cutoff = gen_dt - timedelta(minutes=70)

def is_new_job(j) -> bool:
    ts = j.get("first_seen_ts", "")
    if not ts:
        return False
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ") >= _new_cutoff
    except Exception:
        return False

new_last_hour = sum(1 for j in data if is_new_job(j))
print(f"最近一小时新增 {new_last_hour} 个职位")

# ── 构建 JS 数据 ──────────────────────────────────────────────────────────────
js_locations = []
for name, grp in loc_groups.items():
    jobs_js = []
    for j in grp["jobs"]:
        color  = LABEL_COLORS.get(j.get("label", ""), "#888")
        src    = j.get("source", "")
        sal_txt = j.get("salary", "") or "薪资面议"
        eff_date = (j.get("effective_date") or j.get("posted_date")
                    or j.get("first_seen") or "")
        jobs_js.append({
            "title":   j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "salary":  sal_txt,
            "sal_num": parse_sal_num(sal_txt),
            "snippet": j.get("snippet", ""),
            "url":     j.get("url", "#"),
            "label":   j.get("label", ""),
            "color":   color,
            "posted":  j.get("posted", ""),
            "date":    eff_date,
            "source":  src,
            "src_color": SOURCE_COLORS.get(src, "#888"),
            "is_new":  is_new_job(j),
        })
    js_locations.append({
        "name": name,
        "lat":  grp["lat"],
        "lng":  grp["lng"],
        "jobs": jobs_js,
    })

js_data = json.dumps(js_locations, ensure_ascii=False)

# 更新时间（转香港时间 UTC+8）
try:
    latest_ts = max((j.get("scraped_at","") for j in data), default="")
    if latest_ts:
        dt = datetime.strptime(latest_ts, "%Y-%m-%dT%H:%M:%SZ") + timedelta(hours=8)
        update_str = dt.strftime("%Y-%m-%d %H:%M")
    else:
        update_str = "—"
except Exception:
    update_str = "—"

# 香港当前日期 + 昨日新增岗位统计
hkt_now   = datetime.utcnow() + timedelta(hours=8)
gen_date  = hkt_now.date().isoformat()
yesterday = (hkt_now.date() - timedelta(days=1)).isoformat()
new_yesterday = sum(1 for j in data if j.get("first_seen") == yesterday)
total_located = sum(len(g["jobs"]) for g in loc_groups.values())
source_badge_html = " ".join(
    f'<span style="background:{SOURCE_COLORS.get(s,"#888")};color:#fff;'
    f'padding:2px 7px;border-radius:4px;font-size:.7rem;font-weight:700">{s} {c}</span>'
    for s, c in source_counts.items()
)

# 分类下拉选项（颜色与 LABEL_COLORS 保持同步）
cat_items_html = (
    '<div class="cat-item on" data-cat="all">'
    '<span class="cat-dot" style="background:#16a34a"></span>全部分类</div>\n'
)
for _lbl, _col in LABEL_COLORS.items():
    cat_items_html += (
        f'<div class="cat-item" data-cat="{_lbl}">'
        f'<span class="cat-dot" style="background:{_col}"></span>{_lbl}</div>\n'
    )

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>秒投 · 香港求职地图</title>
<meta name="theme-color" content="#16a34a">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="秒投">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;
     display:flex;flex-direction:column;height:100vh;overflow:hidden;background:#f0fdf4}}

/* ── header ── */
.hdr{{background:#fff;border-bottom:1px solid #d1fae5;
      box-shadow:0 1px 10px rgba(16,163,74,.07);
      padding:10px 18px;display:flex;align-items:center;gap:14px;flex-shrink:0;z-index:1000;
      flex-wrap:wrap}}
.hdr-left{{display:flex;flex-direction:column;gap:3px}}
.brand{{display:flex;align-items:center;gap:8px}}
.brand-logo{{width:32px;height:32px;border-radius:10px;
      background:linear-gradient(135deg,#4ade80,#16a34a);
      display:flex;align-items:center;justify-content:center;font-size:1.05rem;
      box-shadow:0 3px 8px rgba(22,163,74,.4)}}
.hdr h1{{font-size:1.35rem;font-weight:800;color:#15803d;letter-spacing:2px}}
.brand .slogan{{font-size:.7rem;color:#22c55e;font-weight:700;letter-spacing:.5px;
      padding-left:4px;border-left:2px solid #bbf7d0;margin-left:2px}}
.hdr-meta{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:1px}}
.hdr-info{{font-size:.75rem;color:#64748b}}
.hdr-info strong{{color:#16a34a}}
.hdr-right{{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-left:auto}}

/* ── 分类下拉 ── */
.cat-dd{{position:relative}}
.cat-btn{{display:flex;align-items:center;gap:7px;padding:8px 14px;
      background:#f0fdf4;border:1.5px solid #86efac;border-radius:10px;
      font-size:.83rem;font-weight:700;color:#15803d;cursor:pointer;white-space:nowrap}}
.cat-btn:hover{{background:#dcfce7;border-color:#22c55e}}
.cat-btn .arrow{{font-size:.58rem;transition:transform .18s}}
.cat-dd.open .cat-btn .arrow{{transform:rotate(180deg)}}
.cat-panel{{position:absolute;top:calc(100% + 7px);left:0;z-index:2000;
      background:#fff;border:1px solid #d1fae5;border-radius:13px;
      box-shadow:0 10px 32px rgba(16,163,74,.2);padding:7px;
      display:none;grid-template-columns:1fr 1fr;gap:2px;width:292px}}
.cat-dd.open .cat-panel{{display:grid}}
.cat-item{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:9px;
      font-size:.8rem;font-weight:600;color:#475569;cursor:pointer;transition:.1s}}
.cat-item:hover{{background:#f0fdf4}}
.cat-item.on{{background:#dcfce7;color:#15803d;font-weight:700}}
.cat-dot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}

/* ── 日期筛选 ── */
.date-filters{{display:flex;gap:4px;align-items:center}}
.date-filters .lbl{{font-size:.74rem;color:#64748b;font-weight:700;margin-right:2px}}
.dtag{{padding:6px 12px;border-radius:9px;font-size:.77rem;font-weight:700;
       cursor:pointer;transition:.15s;white-space:nowrap;
       background:#f0fdf4;color:#15803d;border:1.5px solid transparent}}
.dtag:hover{{background:#dcfce7}}
.dtag.on{{background:linear-gradient(135deg,#4ade80,#16a34a);color:#fff;
          box-shadow:0 2px 7px rgba(22,163,74,.4)}}
.resume-btn{{padding:8px 15px;background:linear-gradient(135deg,#4ade80,#16a34a);
             color:#fff;border-radius:10px;font-size:.81rem;font-weight:700;
             text-decoration:none;white-space:nowrap;
             box-shadow:0 2px 8px rgba(22,163,74,.35)}}
.resume-btn:hover{{filter:brightness(1.08)}}

/* ── 视图切换 地图/列表 ── */
.view-toggle{{display:flex;background:#f0fdf4;border:1.5px solid #86efac;
      border-radius:10px;overflow:hidden;flex-shrink:0}}
.vt-btn{{padding:7px 13px;font-size:.8rem;font-weight:700;border:none;
      background:transparent;color:#15803d;cursor:pointer;white-space:nowrap}}
.vt-btn.on{{background:linear-gradient(135deg,#4ade80,#16a34a);color:#fff}}

/* ── main layout ── */
.main{{display:flex;flex:1;overflow:hidden;position:relative}}
#map{{flex:1;z-index:1}}

/* ── 列表视图 ── */
#list-view{{flex:1;display:none;flex-direction:column;background:#f0fdf4;overflow:hidden}}
.list-bar{{display:flex;gap:8px;padding:10px 14px;background:#fff;
      border-bottom:1px solid #d1fae5;flex-shrink:0}}
.list-bar input{{flex:1;padding:8px 12px;border:1.5px solid #d1fae5;
      border-radius:9px;font-size:.85rem;outline:none}}
.list-bar input:focus{{border-color:#22c55e}}
.list-sub{{padding:8px 16px 2px;font-size:.78rem;color:#64748b;flex-shrink:0;
      max-width:680px;width:100%;margin:0 auto}}
.list-sub strong{{color:#16a34a}}
.list-body{{flex:1;overflow-y:auto;padding:6px 12px 20px;
      display:flex;flex-direction:column;gap:9px;
      max-width:680px;width:100%;margin:0 auto}}
.more-btn{{margin:10px auto 0;padding:11px 26px;
      background:#fff;border:1.5px solid #86efac;border-radius:11px;
      color:#15803d;font-weight:700;font-size:.84rem;cursor:pointer}}
.more-btn:hover{{background:#dcfce7}}

/* ── sidebar ── */
.side{{width:390px;background:#fff;display:flex;flex-direction:column;
       border-left:1px solid #d1fae5;overflow:hidden;transition:width .25s;flex-shrink:0}}
.side.closed{{width:0}}
.sheet-handle{{display:none}}
.side-hdr{{padding:13px 15px 9px;border-bottom:1px solid #d1fae5;flex-shrink:0;
           background:#f0fdf4}}
.side-hdr h2{{font-size:.98rem;color:#15803d;font-weight:800}}
.side-hdr .sub{{font-size:.78rem;color:#64748b;margin-top:3px}}
.side-close{{float:right;cursor:pointer;width:30px;height:30px;border-radius:50%;
             background:#e2e8f0;color:#475569;font-size:1rem;font-weight:800;
             text-align:center;line-height:30px}}
.side-close:hover{{background:#fecaca;color:#dc2626}}
.side-search{{padding:9px 14px;border-bottom:1px solid #d1fae5;flex-shrink:0;
              display:flex;gap:6px;align-items:center}}
.side-search input{{flex:1;padding:7px 11px;border:1.5px solid #d1fae5;
                    border-radius:8px;font-size:.83rem;outline:none}}
.side-search input:focus{{border-color:#22c55e}}
.sort-btn{{padding:6px 9px;border:1.5px solid #d1fae5;border-radius:8px;
           font-size:.75rem;color:#15803d;font-weight:700;cursor:pointer;
           white-space:nowrap;background:#fff}}
.sort-btn:hover{{background:#f0fdf4;border-color:#22c55e}}
.job-list{{flex:1;overflow-y:auto;padding:9px 11px;display:flex;flex-direction:column;gap:9px}}

/* ── job card ── */
.jcard{{border-radius:11px;border:1px solid #e2e8f0;border-left:4px solid #86efac;
        transition:.15s;background:#fff}}
.jcard:hover{{box-shadow:0 4px 16px rgba(16,163,74,.14);border-left-color:#16a34a}}
.jc-body{{padding:11px 13px 0}}
.jc-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:3px}}
.jc-title{{font-size:.88rem;font-weight:700;color:#1e293b;text-decoration:none;line-height:1.35;flex:1}}
.jc-title:hover{{color:#16a34a;text-decoration:underline}}
.jc-src{{font-size:.65rem;font-weight:700;padding:2px 6px;border-radius:4px;
         color:#fff;flex-shrink:0;align-self:flex-start;margin-top:2px}}
.jc-co{{font-size:.8rem;font-weight:600;color:#475569;margin-bottom:7px}}
.jc-sal{{display:flex;align-items:center;gap:6px;padding:6px 10px;
         background:#f0fdf4;border-radius:7px;margin-bottom:7px}}
.jc-sal-icon{{font-size:.85rem}}
.jc-sal-txt{{font-size:.85rem;font-weight:800;color:#15803d}}
.jc-sal-none{{font-size:.8rem;color:#94a3b8;font-style:italic}}
.jc-tags{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:7px}}
.badge{{border-radius:5px;padding:2px 7px;font-weight:600;font-size:.72rem}}
.b-cat{{color:#fff}}
.b-loc{{background:#dcfce7;color:#15803d}}
.b-dat{{background:#f1f5f9;color:#64748b;font-weight:400}}
.jd-tabs{{display:flex;border-top:1px solid #f0fdf4;margin-top:2px}}
.jd-tab{{flex:1;padding:6px 0;font-size:.72rem;font-weight:600;text-align:center;
         cursor:pointer;color:#94a3b8;background:#f8fafc;
         border-bottom:2px solid transparent;transition:.1s;user-select:none}}
.jd-tab:hover{{color:#16a34a}}
.jd-tab.on{{color:#16a34a;border-bottom-color:#16a34a;background:#fff}}
.jd-panel{{padding:9px 13px;font-size:.78rem;color:#475569;line-height:1.6;
           display:none;max-height:90px;overflow-y:auto;background:#fff}}
.jd-panel.on{{display:block}}
.jd-panel em{{color:#b0bec5;font-style:italic}}
.jc-foot{{padding:7px 13px 11px;display:flex;justify-content:flex-end;gap:6px;
          border-top:1px solid #f0fdf4}}
.btn{{display:inline-block;padding:6px 13px;border-radius:7px;text-decoration:none;
      font-size:.74rem;font-weight:700;color:#fff}}
.btn-apply{{background:linear-gradient(135deg,#4ade80,#16a34a);
            box-shadow:0 2px 6px rgba(22,163,74,.32)}}
.btn-apply:hover{{filter:brightness(1.08)}}
.btn-cv{{background:#0d9488}}
.btn-cv:hover{{background:#0f766e}}

/* ── map marker ── */
.mk-wrap{{position:relative;display:flex;flex-direction:column;align-items:center}}
.mk-circle{{width:30px;height:30px;border-radius:50%;
            background:linear-gradient(135deg,#4ade80,#16a34a);
            border:2.5px solid #fff;box-shadow:0 2px 7px rgba(22,163,74,.45);
            display:flex;align-items:center;justify-content:center;
            color:#fff;font-size:.66rem;font-weight:800;cursor:pointer;
            transition:transform .15s}}
.mk-circle:hover{{transform:scale(1.15)}}
.mk-circle.active{{background:linear-gradient(135deg,#15803d,#14532d);transform:scale(1.22)}}
.mk-label{{background:rgba(21,128,61,.85);color:#fff;font-size:.62rem;font-weight:600;
           padding:2px 6px;border-radius:4px;white-space:nowrap;margin-top:3px;
           pointer-events:none}}

.empty{{padding:36px 20px;text-align:center;color:#94a3b8;font-size:.88rem}}

/* ── 新岗位提醒条 ── */
.notify-bar{{display:none;align-items:center;gap:10px;
     background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;
     padding:9px 16px;font-size:.85rem;font-weight:600;flex-shrink:0;
     box-shadow:0 2px 8px rgba(16,163,74,.25)}}
.notify-bar.show{{display:flex}}
.nb-text strong{{font-size:1.05rem;margin:0 2px}}
.nb-view{{margin-left:auto;padding:6px 15px;background:#fff;color:#15803d;
     border:none;border-radius:8px;font-weight:800;font-size:.8rem;cursor:pointer}}
.nb-view:hover{{background:#dcfce7}}
.nb-close{{cursor:pointer;font-size:1.05rem;opacity:.85;padding:0 3px;
     flex-shrink:0}}
.nb-close:hover{{opacity:1}}
/* 刷新提示气泡 */
.refresh-toast{{position:fixed;bottom:20px;left:50%;
     transform:translateX(-50%) translateY(180%);
     background:#15803d;color:#fff;padding:12px 22px;border-radius:13px;
     font-size:.85rem;font-weight:700;cursor:pointer;z-index:3000;
     box-shadow:0 8px 28px rgba(0,0,0,.32);transition:transform .32s}}
.refresh-toast.show{{transform:translateX(-50%) translateY(0)}}
/* 新岗位徽章 + 「仅看新增」chip */
.badge-new{{background:#16a34a;color:#fff}}
.new-chip{{display:inline-flex;align-items:center;gap:4px;cursor:pointer;
     background:#16a34a;color:#fff;padding:2px 9px;border-radius:11px;
     font-size:.74rem;font-weight:700;margin-right:6px}}
.new-chip:hover{{background:#15803d}}

@media(max-width:768px){{
  /* 顶栏紧凑化 */
  .hdr{{padding:7px 11px;gap:6px}}
  .brand-logo{{width:26px;height:26px;font-size:.92rem;border-radius:8px}}
  .hdr h1{{font-size:1.12rem;letter-spacing:1px}}
  .brand .slogan{{display:none}}
  .src-badges{{display:none}}
  .hdr-info{{font-size:.7rem}}
  .hdr-right{{width:100%;margin-left:0;gap:6px;flex-wrap:wrap}}
  .date-filters .lbl{{display:none}}
  .date-filters{{gap:5px;flex-shrink:0}}
  .dtag{{padding:6px 11px;font-size:.75rem}}
  .cat-btn{{padding:7px 12px;font-size:.79rem}}
  .resume-btn{{padding:7px 12px;font-size:.77rem}}
  .cat-panel{{width:min(300px,calc(100vw - 22px))}}

  /* 地图标记缩小 */
  .mk-circle{{width:26px;height:26px;font-size:.6rem;border-width:2px}}
  .mk-label{{display:none}}

  /* 职位面板 → 填满页头以下整块区域，关闭按钮永远在页头正下方 */
  .side{{position:absolute;top:0;right:0;bottom:0;left:0;z-index:600;
         width:auto;height:auto;border-left:none;border-radius:0;
         box-shadow:0 -6px 24px rgba(0,0,0,.18);
         transform:translateY(0);transition:transform .28s ease}}
  .side.closed{{width:auto;transform:translateY(100%)}}
  .sheet-handle{{display:block;width:46px;height:5px;border-radius:3px;
                 background:#86efac;margin:7px auto 0;flex-shrink:0;cursor:pointer}}
  .side-hdr{{padding:6px 14px 10px}}
  .side-close{{width:40px;height:40px;line-height:40px;font-size:1.3rem;
               background:#dcfce7;color:#15803d}}
  .side-close:active{{background:#bbf7d0}}
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <div class="brand">
      <div class="brand-logo">⚡</div>
      <h1>秒投</h1>
      <span class="slogan">你的一键求职搭子</span>
    </div>
    <div class="hdr-meta">
      <span class="hdr-info">共 <strong id="total-count">{total_located}</strong> 个职位 · 昨日新增 <strong>{new_yesterday}</strong> · 更新于 {update_str} HKT</span>
      <span class="src-badges">{source_badge_html}</span>
    </div>
  </div>

  <div class="hdr-right">
    <div class="view-toggle" id="view-toggle">
      <button class="vt-btn on" data-view="map">🗺 地图</button>
      <button class="vt-btn" data-view="list">📋 列表</button>
    </div>
    <div class="cat-dd" id="cat-dd">
      <button class="cat-btn" id="cat-btn">
        <span id="cat-btn-label">🏷 全部分类</span>
        <span class="arrow">▼</span>
      </button>
      <div class="cat-panel" id="cat-panel">
        {cat_items_html}
      </div>
    </div>
    <div class="date-filters" id="date-filters">
      <span class="lbl">📅 发布</span>
      <span class="dtag" data-days="3">近3天</span>
      <span class="dtag" data-days="5">近5天</span>
      <span class="dtag on" data-days="7">近7天</span>
      <span class="dtag" data-days="0">全部</span>
    </div>
    <a href="resume.html" class="resume-btn">📄 生成简历</a>
  </div>
</div>

<div class="notify-bar" id="notify-bar">
  <span class="nb-text">🔔 最近一小时新增 <strong id="nb-count">0</strong> 个职位</span>
  <button class="nb-view" id="nb-view">查看新职位</button>
  <span class="nb-close" id="nb-close" title="关闭">✕</span>
</div>

<div class="main">
  <div id="map"></div>

  <div id="list-view">
    <div class="list-bar">
      <input id="list-q" type="text" placeholder="搜索职位 / 公司…">
      <button class="sort-btn" id="list-sort" title="切换排序">💰 薪资</button>
    </div>
    <div class="list-sub" id="list-count"></div>
    <div class="list-body" id="list-body"></div>
  </div>

  <div class="side closed" id="side">
    <div class="sheet-handle" id="sheet-handle"></div>
    <div class="side-hdr">
      <span class="side-close" id="side-close">✕</span>
      <h2 id="side-title">选择地点</h2>
      <div class="sub" id="side-sub"></div>
    </div>
    <div class="side-search">
      <input id="side-q" type="text" placeholder="搜索职位 / 公司…">
      <button class="sort-btn" id="sort-btn" title="切换排序">💰 薪资</button>
    </div>
    <div class="job-list" id="job-list"></div>
  </div>
</div>

<div class="refresh-toast" id="refresh-toast">🔄 有新一批职位 · 点此刷新</div>

<script>
const LOCATIONS = {js_data};
const ALL_JOBS  = LOCATIONS.flatMap(l => l.jobs);
let currentView = 'map';

const isMobile = window.matchMedia('(max-width:768px)').matches;
const map = L.map('map', {{
  center: [22.3193, 114.1694],
  zoom: isMobile ? 11 : 12,
  zoomControl: !isMobile,
}});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
  maxZoom: 18,
}}).addTo(map);

let activeCategory = 'all';
let activeMarkerEl = null;
let currentJobs    = [];
let sortBySalary   = false;
let activeDays     = 7;   // 默认只看近7天
let showOnlyNew    = false;

const TODAY     = new Date("{gen_date}T00:00:00Z");
const NEW_COUNT = {new_last_hour};
const GEN_TS    = "{gen_ts_iso}";

function jobAgeDays(j) {{
  if (!j.date) return 9999;
  const d = new Date(j.date + "T00:00:00Z");
  if (isNaN(d)) return 9999;
  return Math.floor((TODAY - d) / 86400000);
}}
function dateOk(j) {{
  return activeDays === 0 || jobAgeDays(j) <= activeDays;
}}
function catOk(j) {{
  return activeCategory === 'all' || j.label === activeCategory;
}}
function ageLabel(j) {{
  const a = jobAgeDays(j);
  if (a >= 9999) return '';
  if (a <= 0) return '今天';
  if (a === 1) return '昨天';
  return a + '天前';
}}
// 薪资排序：有薪资的按高→低，"面议"(无薪资)统一排最后
function salCmp(a, b) {{
  if (a.sal_num && b.sal_num) return b.sal_num - a.sal_num;
  if (a.sal_num) return -1;
  if (b.sal_num) return 1;
  return jobAgeDays(a) - jobAgeDays(b);
}}

// ── 标记 ──────────────────────────────────────────────────────────────────────
const markers = [];
LOCATIONS.forEach((loc, idx) => {{
  const icon = L.divIcon({{
    className: '',
    html: `<div class="mk-wrap">
      <div class="mk-circle" id="mk-${{idx}}">${{loc.jobs.length}}</div>
      <div class="mk-label">${{loc.name.split(' ')[0]}}</div>
    </div>`,
    iconSize: [50, 52],
    iconAnchor: [25, 18],
  }});
  const marker = L.marker([loc.lat, loc.lng], {{ icon }}).addTo(map);
  marker.on('click', () => openSidebar(loc, idx));
  markers.push({{ marker, loc, idx }});
}});

// ── 刷新所有标记数字 + 总数 ───────────────────────────────────────────────────
function refreshMarkers() {{
  let total = 0;
  LOCATIONS.forEach((loc, idx) => {{
    const cnt = loc.jobs.filter(j => catOk(j) && dateOk(j)).length;
    total += cnt;
    const el = document.getElementById('mk-' + idx);
    if (el) {{
      el.textContent = cnt;
      el.style.opacity = cnt > 0 ? '1' : '0.25';
    }}
  }});
  const tc = document.getElementById('total-count');
  if (tc) tc.textContent = total;
}}
refreshMarkers();

// ── 侧边栏 ────────────────────────────────────────────────────────────────────
function openSidebar(loc, idx) {{
  if (activeMarkerEl) activeMarkerEl.classList.remove('active');
  const mkEl = document.getElementById('mk-' + idx);
  if (mkEl) {{ mkEl.classList.add('active'); activeMarkerEl = mkEl; }}
  currentJobs = loc.jobs;
  document.getElementById('side-title').textContent = loc.name;
  document.getElementById('side-q').value = '';
  renderJobs(loc.jobs);
  document.getElementById('side').classList.remove('closed');
}}

function closeSidebar() {{
  document.getElementById('side').classList.add('closed');
  if (activeMarkerEl) {{ activeMarkerEl.classList.remove('active'); activeMarkerEl = null; }}
}}

document.getElementById('side-close').addEventListener('click', closeSidebar);
document.getElementById('sheet-handle').addEventListener('click', closeSidebar);
// 点地图空白处也能关闭职位列表
map.on('click', closeSidebar);

document.getElementById('side-q').addEventListener('input', e => {{
  const q = e.target.value.trim().toLowerCase();
  const filtered = q
    ? currentJobs.filter(j => (j.title+j.company+j.snippet).toLowerCase().includes(q))
    : currentJobs;
  renderJobs(filtered);
}});

document.getElementById('sort-btn').addEventListener('click', () => {{
  sortBySalary = !sortBySalary;
  document.getElementById('sort-btn').textContent = sortBySalary ? '🕐 最新' : '💰 薪资';
  renderJobs(currentJobs);
}});

function renderJobs(jobs) {{
  let filtered = jobs.filter(j => catOk(j) && dateOk(j));

  filtered.sort(sortBySalary ? salCmp : (a, b) => jobAgeDays(a) - jobAgeDays(b));

  const dLabel = activeDays === 0 ? '全部' : `近${{activeDays}}天`;
  document.getElementById('side-sub').textContent =
    `${{filtered.length}} 个职位 · ${{dLabel}}` +
    (activeCategory !== 'all' ? `（${{activeCategory}}）` : '');

  const list = document.getElementById('job-list');
  list.innerHTML = filtered.length
    ? filtered.map(buildCard).join('')
    : '<div class="empty">该地区暂无此类职位</div>';
}}

// ── 职位卡片（地图侧栏 + 列表视图共用）───────────────────────────────────────
function buildCard(j) {{
  const hasSal = j.salary && j.salary !== '薪资面议';
  const salRow = hasSal
    ? `<div class="jc-sal"><span class="jc-sal-icon">💰</span><span class="jc-sal-txt">${{j.salary}}</span></div>`
    : `<div class="jc-sal"><span class="jc-sal-icon">💰</span><span class="jc-sal-none">薪资面议</span></div>`;
  const jdEnc = encodeURIComponent((j.snippet || '').substring(0, 500));
  const al = ageLabel(j);
  let dateBadge = '';
  if (al) {{
    const fresh = jobAgeDays(j) <= 2;
    dateBadge = `<span class="badge" style="background:${{fresh?'#dcfce7':'#f1f5f9'}};`
              + `color:${{fresh?'#166534':'#64748b'}}">🕐 ${{al}}</span>`;
  }} else if (j.posted) {{
    dateBadge = `<span class="badge b-dat">🕐 ${{j.posted}}</span>`;
  }}
  return `
  <div class="jcard">
    <div class="jc-body">
      <div class="jc-top">
        <a class="jc-title" href="${{j.url}}" target="_blank">${{j.title}}</a>
        <span class="jc-src" style="background:${{j.src_color}}">${{j.source}}</span>
      </div>
      <div class="jc-co">${{j.company}}</div>
      ${{salRow}}
      <div class="jc-tags">
        ${{j.is_new ? '<span class="badge badge-new">🆕 新</span>' : ''}}
        <span class="badge b-cat" style="background:${{j.color}}">${{j.label}}</span>
        <span class="badge b-loc">📍 ${{j.location || '不限地区'}}</span>
        ${{dateBadge}}
      </div>
      ${{j.snippet ? `<div class="jd-panel on">${{j.snippet}}</div>` : ''}}
    </div>
    <div class="jc-foot">
      <a class="btn btn-apply" href="${{j.url}}" target="_blank">查看完整JD →</a>
      ${{jdEnc ? `<a class="btn btn-cv" href="resume.html?jd=${{jdEnc}}" target="_blank">✨ 匹配简历</a>` : ''}}
    </div>
  </div>`;
}}

// ── 分类过滤 ──────────────────────────────────────────────────────────────────
const catDd = document.getElementById('cat-dd');
document.getElementById('cat-btn').addEventListener('click', e => {{
  e.stopPropagation();
  catDd.classList.toggle('open');
}});
document.addEventListener('click', () => catDd.classList.remove('open'));

document.getElementById('cat-panel').addEventListener('click', e => {{
  e.stopPropagation();
  const item = e.target.closest('.cat-item');
  if (!item) return;
  activeCategory = item.dataset.cat;
  document.querySelectorAll('.cat-item').forEach(t => t.classList.remove('on'));
  item.classList.add('on');
  document.getElementById('cat-btn-label').textContent =
    '🏷 ' + (activeCategory === 'all' ? '全部分类' : activeCategory);
  catDd.classList.remove('open');
  refreshMarkers();
  if (!document.getElementById('side').classList.contains('closed')) {{
    renderJobs(currentJobs);
  }}
  if (currentView === 'list') renderList();
}});

// ── 日期过滤 ──────────────────────────────────────────────────────────────────
document.getElementById('date-filters').addEventListener('click', e => {{
  const tag = e.target.closest('.dtag');
  if (!tag) return;
  activeDays = parseInt(tag.dataset.days, 10);
  document.querySelectorAll('.dtag').forEach(t => t.classList.remove('on'));
  tag.classList.add('on');
  refreshMarkers();
  if (!document.getElementById('side').classList.contains('closed')) {{
    renderJobs(currentJobs);
  }}
  if (currentView === 'list') renderList();
}});

// ── 列表视图 ──────────────────────────────────────────────────────────────────
let listLimit = 80;
function getListJobs() {{
  let arr = ALL_JOBS.filter(j => catOk(j) && dateOk(j));
  if (showOnlyNew) arr = arr.filter(j => j.is_new);
  const q = document.getElementById('list-q').value.trim().toLowerCase();
  if (q) arr = arr.filter(j => (j.title + j.company + j.snippet).toLowerCase().includes(q));
  arr = arr.slice();
  arr.sort(sortBySalary ? salCmp : (a, b) => jobAgeDays(a) - jobAgeDays(b));
  return arr;
}}
function renderList(resetLimit) {{
  if (resetLimit !== false) listLimit = 80;
  const arr = getListJobs();
  const dLabel = activeDays === 0 ? '全部时间' : `近${{activeDays}}天`;
  const newChip = showOnlyNew
    ? '<span class="new-chip" id="new-chip">🆕 仅看新增 ✕</span>' : '';
  document.getElementById('list-count').innerHTML = newChip +
    `共 <strong>${{arr.length}}</strong> 个职位 · ${{dLabel}}` +
    (activeCategory !== 'all' ? ` · ${{activeCategory}}` : '');
  const body = document.getElementById('list-body');
  if (!arr.length) {{
    body.innerHTML = '<div class="empty">没有符合条件的职位</div>';
    return;
  }}
  body.innerHTML = arr.slice(0, listLimit).map(buildCard).join('');
  if (arr.length > listLimit) {{
    const btn = document.createElement('button');
    btn.className = 'more-btn';
    btn.textContent = `加载更多（还有 ${{arr.length - listLimit}} 个）`;
    btn.onclick = () => {{ listLimit += 120; renderList(false); }};
    body.appendChild(btn);
  }}
}}
document.getElementById('list-q').addEventListener('input', () => renderList());
document.getElementById('list-sort').addEventListener('click', () => {{
  sortBySalary = !sortBySalary;
  document.getElementById('list-sort').textContent = sortBySalary ? '🕐 最新' : '💰 薪资';
  renderList();
}});

// ── 视图切换 地图/列表 ────────────────────────────────────────────────────────
document.getElementById('view-toggle').addEventListener('click', e => {{
  const b = e.target.closest('.vt-btn');
  if (!b) return;
  currentView = b.dataset.view;
  document.querySelectorAll('.vt-btn').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  const listMode = currentView === 'list';
  document.getElementById('map').style.display = listMode ? 'none' : '';
  document.getElementById('list-view').style.display = listMode ? 'flex' : 'none';
  closeSidebar();
  if (listMode) renderList();
  else setTimeout(() => map.invalidateSize(), 60);
}});

// ── 新岗位提醒 ────────────────────────────────────────────────────────────────
if (NEW_COUNT > 0) {{
  document.getElementById('nb-count').textContent = NEW_COUNT;
  document.getElementById('notify-bar').classList.add('show');
}}
document.getElementById('nb-close').addEventListener('click', () => {{
  document.getElementById('notify-bar').classList.remove('show');
}});
document.getElementById('nb-view').addEventListener('click', () => {{
  showOnlyNew = true;
  document.getElementById('notify-bar').classList.remove('show');
  document.querySelector('.vt-btn[data-view="list"]').click();
}});
// 列表里点「仅看新增 ✕」chip 取消筛选
document.getElementById('list-count').addEventListener('click', e => {{
  if (e.target.id === 'new-chip') {{ showOnlyNew = false; renderList(); }}
}});

// ── 每10分钟检查是否有新一轮更新 ──────────────────────────────────────────────
const refreshToast = document.getElementById('refresh-toast');
refreshToast.addEventListener('click', () => location.reload());
async function checkUpdates() {{
  try {{
    const v = await fetch('/version.json?_=' + Date.now(), {{cache:'no-store'}})
                      .then(r => r.json());
    if (v.generated_at && v.generated_at > GEN_TS) {{
      refreshToast.textContent = v.new_last_hour > 0
        ? `🔄 新增 ${{v.new_last_hour}} 个职位 · 点此刷新`
        : '🔄 职位已更新 · 点此刷新';
      refreshToast.classList.add('show');
    }}
  }} catch (e) {{}}
}}
setInterval(checkUpdates, 10 * 60 * 1000);

// ── PWA Service Worker ────────────────────────────────────────────────────────
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', () => {{
    navigator.serviceWorker.register('/sw.js').catch(() => {{}});
  }});
}}
</script>
</body></html>"""

OUTPUT_FILE.write_text(html, encoding="utf-8")

# version.json — 供前端轮询检测「是否有新一轮更新」
(OUTPUT_FILE.parent / "version.json").write_text(
    json.dumps({"generated_at": gen_ts_iso, "new_last_hour": new_last_hour}),
    encoding="utf-8")

print(f"✅ 地图已生成: {OUTPUT_FILE.resolve()}")
print(f"   {len(loc_groups)} 个地点 · {total_located} 个职位已标注")


if __name__ == "__main__" and "--open" in sys.argv:
    import subprocess
    subprocess.Popen(["open", str(OUTPUT_FILE)])
