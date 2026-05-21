#!/usr/bin/env python3
"""
HK Jobs 地图生成器 — Multi-platform edition
读取 data/jobs.json，生成交互式香港地图 index.html
"""

import json, re, sys
from pathlib import Path
from datetime import datetime

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
    "JobsDB": "#e60028",
    "Indeed": "#2164f3",
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

# ── 构建 JS 数据 ──────────────────────────────────────────────────────────────
js_locations = []
for name, grp in loc_groups.items():
    jobs_js = []
    for j in grp["jobs"]:
        color  = LABEL_COLORS.get(j.get("label", ""), "#888")
        src    = j.get("source", "")
        sal_txt = j.get("salary", "") or "薪资面议"
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
            "source":  src,
            "src_color": SOURCE_COLORS.get(src, "#888"),
            "scraped_at": j.get("scraped_at", ""),
        })
    js_locations.append({
        "name": name,
        "lat":  grp["lat"],
        "lng":  grp["lng"],
        "jobs": jobs_js,
    })

js_data = json.dumps(js_locations, ensure_ascii=False)

# scrape timestamp
try:
    latest_ts = max((j.get("scraped_at","") for j in data), default="")
    if latest_ts:
        dt = datetime.strptime(latest_ts, "%Y-%m-%dT%H:%M:%SZ")
        update_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        update_str = "—"
except Exception:
    update_str = "—"

total_located = sum(len(g["jobs"]) for g in loc_groups.values())
source_badge_html = " ".join(
    f'<span style="background:{SOURCE_COLORS.get(s,"#888")};color:#fff;'
    f'padding:3px 8px;border-radius:4px;font-size:.75rem;font-weight:700">{s} {c}</span>'
    for s, c in source_counts.items()
)

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HK Jobs Map — JobsDB + Indeed</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
     display:flex;flex-direction:column;height:100vh;overflow:hidden;background:#f1f5f9}}

/* ── header ── */
.hdr{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;
      padding:10px 16px;display:flex;align-items:center;gap:14px;flex-shrink:0;z-index:1000;
      flex-wrap:wrap}}
.hdr-left{{display:flex;flex-direction:column;gap:3px}}
.hdr h1{{font-size:1.1rem;white-space:nowrap}}
.hdr-meta{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.hdr-info{{font-size:.78rem;opacity:.75}}
.hdr-filters{{display:flex;gap:5px;flex-wrap:wrap;margin-left:auto}}
.ftag{{padding:3px 9px;border-radius:14px;border:1.5px solid rgba(255,255,255,.5);
       font-size:.72rem;font-weight:600;cursor:pointer;color:rgba(255,255,255,.75);
       transition:.15s;white-space:nowrap}}
.ftag.on{{background:rgba(255,255,255,.2);color:#fff;border-color:#fff}}
.ftag:hover{{border-color:#fff;color:#fff}}
.resume-btn{{padding:6px 13px;background:rgba(255,255,255,.15);color:#fff;
             border-radius:6px;font-size:.8rem;font-weight:600;text-decoration:none;
             border:1.5px solid rgba(255,255,255,.35);white-space:nowrap}}
.resume-btn:hover{{background:rgba(255,255,255,.25)}}

/* ── main layout ── */
.main{{display:flex;flex:1;overflow:hidden}}
#map{{flex:1;z-index:1}}

/* ── sidebar ── */
.side{{width:390px;background:#fff;display:flex;flex-direction:column;
       border-left:1px solid #e2e8f0;overflow:hidden;transition:width .25s;flex-shrink:0}}
.side.closed{{width:0}}
.side-hdr{{padding:12px 14px 8px;border-bottom:1px solid #e2e8f0;flex-shrink:0}}
.side-hdr h2{{font-size:.95rem;color:#1e293b}}
.side-hdr .sub{{font-size:.78rem;color:#64748b;margin-top:3px}}
.side-close{{float:right;cursor:pointer;font-size:1.1rem;color:#94a3b8;line-height:1}}
.side-close:hover{{color:#e60028}}
.side-search{{padding:8px 14px;border-bottom:1px solid #e2e8f0;flex-shrink:0;
              display:flex;gap:6px;align-items:center}}
.side-search input{{flex:1;padding:6px 10px;border:1px solid #cbd5e1;
                    border-radius:6px;font-size:.83rem;outline:none}}
.side-search input:focus{{border-color:#1a1a2e}}
.sort-btn{{padding:5px 8px;border:1px solid #cbd5e1;border-radius:6px;
           font-size:.75rem;color:#475569;cursor:pointer;white-space:nowrap;background:#fff}}
.sort-btn:hover{{background:#f8fafc}}
.job-list{{flex:1;overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:8px}}

/* ── job card ── */
.jcard{{border-radius:8px;border:1px solid #e2e8f0;border-left:4px solid #e2e8f0;
        transition:box-shadow .15s;background:#fff}}
.jcard:hover{{box-shadow:0 3px 12px rgba(0,0,0,.1)}}
.jc-body{{padding:10px 12px 0}}
.jc-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:6px;margin-bottom:3px}}
.jc-title{{font-size:.87rem;font-weight:700;color:#1a1a2e;text-decoration:none;line-height:1.35;flex:1}}
.jc-title:hover{{color:#e60028;text-decoration:underline}}
.jc-src{{font-size:.65rem;font-weight:700;padding:2px 6px;border-radius:3px;
         color:#fff;flex-shrink:0;align-self:flex-start;margin-top:2px}}
.jc-co{{font-size:.8rem;font-weight:600;color:#475569;margin-bottom:7px}}
.jc-sal{{display:flex;align-items:center;gap:6px;padding:5px 9px;
         background:#f0fdf4;border-radius:5px;margin-bottom:7px}}
.jc-sal-icon{{font-size:.85rem}}
.jc-sal-txt{{font-size:.85rem;font-weight:700;color:#166534}}
.jc-sal-none{{font-size:.8rem;color:#94a3b8;font-style:italic}}
.jc-tags{{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:7px}}
.badge{{border-radius:4px;padding:2px 6px;font-weight:600;font-size:.72rem}}
.b-cat{{color:#fff}}
.b-loc{{background:#dbeafe;color:#1e40af}}
.b-dat{{background:#f1f5f9;color:#64748b;font-weight:400}}
.jd-tabs{{display:flex;border-top:1px solid #e2e8f0;margin-top:2px}}
.jd-tab{{flex:1;padding:5px 0;font-size:.72rem;font-weight:600;text-align:center;
         cursor:pointer;color:#94a3b8;background:#f8fafc;
         border-bottom:2px solid transparent;transition:.1s;user-select:none}}
.jd-tab:hover{{color:#1a1a2e}}
.jd-tab.on{{color:#1a1a2e;border-bottom-color:#1a1a2e;background:#fff}}
.jd-panel{{padding:8px 12px;font-size:.78rem;color:#475569;line-height:1.6;
           display:none;max-height:90px;overflow-y:auto;background:#fff}}
.jd-panel.on{{display:block}}
.jd-panel em{{color:#b0bec5;font-style:italic}}
.jc-foot{{padding:6px 12px 10px;display:flex;justify-content:flex-end;gap:5px;
          border-top:1px solid #f1f5f9}}
.btn{{display:inline-block;padding:5px 12px;border-radius:5px;text-decoration:none;
      font-size:.74rem;font-weight:600;color:#fff}}
.btn-apply{{background:#e60028}}
.btn-apply:hover{{background:#b0001e}}
.btn-cv{{background:#7c3aed}}
.btn-cv:hover{{background:#6d28d9}}

/* ── map marker ── */
.mk-wrap{{position:relative;display:flex;flex-direction:column;align-items:center}}
.mk-circle{{width:34px;height:34px;border-radius:50%;background:#1a1a2e;
            border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35);
            display:flex;align-items:center;justify-content:center;
            color:#fff;font-size:.7rem;font-weight:700;cursor:pointer;
            transition:transform .15s}}
.mk-circle:hover{{transform:scale(1.15)}}
.mk-circle.active{{background:#e60028;transform:scale(1.2)}}
.mk-label{{background:rgba(0,0,0,.65);color:#fff;font-size:.62rem;font-weight:600;
           padding:2px 5px;border-radius:3px;white-space:nowrap;margin-top:3px;
           pointer-events:none}}

.empty{{padding:36px 20px;text-align:center;color:#94a3b8;font-size:.88rem}}

@media(max-width:768px){{
  .side{{position:absolute;right:0;top:0;bottom:0;z-index:500;width:320px;
         box-shadow:-4px 0 16px rgba(0,0,0,.15)}}
  .side.closed{{width:0}}
  .hdr-filters{{display:none}}
}}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <h1>🗺 香港求职地图</h1>
    <div class="hdr-meta">
      <span class="hdr-info">共 <strong>{total_located}</strong> 个职位 · 更新于 {update_str}</span>
      {source_badge_html}
    </div>
  </div>
  <a href="resume.html" class="resume-btn">📄 生成简历</a>
  <div class="hdr-filters" id="hdr-filters">
    <span class="ftag on" data-cat="all">全部</span>
    <span class="ftag" data-cat="助理"    style="border-color:#6366f1;color:#c7d2fe">助理</span>
    <span class="ftag" data-cat="运营"    style="border-color:#10b981;color:#a7f3d0">运营</span>
    <span class="ftag" data-cat="行政"    style="border-color:#f59e0b;color:#fde68a">行政</span>
    <span class="ftag" data-cat="统筹"    style="border-color:#ec4899;color:#fbcfe8">统筹</span>
    <span class="ftag" data-cat="内容"    style="border-color:#8b5cf6;color:#ddd6fe">内容</span>
    <span class="ftag" data-cat="文案"    style="border-color:#e11d48;color:#fecdd3">文案</span>
    <span class="ftag" data-cat="编辑"    style="border-color:#0891b2;color:#bae6fd">编辑</span>
    <span class="ftag" data-cat="公关PR"  style="border-color:#7c3aed;color:#ddd6fe">公关PR</span>
    <span class="ftag" data-cat="研究"    style="border-color:#15803d;color:#bbf7d0">研究</span>
    <span class="ftag" data-cat="管培生"  style="border-color:#dc2626;color:#fecaca">管培生</span>
    <span class="ftag" data-cat="项目"    style="border-color:#0f766e;color:#99f6e4">项目</span>
    <span class="ftag" data-cat="市场"    style="border-color:#9333ea;color:#e9d5ff">市场</span>
    <span class="ftag" data-cat="英语教学" style="border-color:#047857;color:#a7f3d0">英语教学</span>
    <span class="ftag" data-cat="法律辅助" style="border-color:#92400e;color:#fde68a">法律辅助</span>
    <span class="ftag" data-cat="翻译"    style="border-color:#b45309;color:#fde68a">翻译</span>
  </div>
</div>

<div class="main">
  <div id="map"></div>

  <div class="side closed" id="side">
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

<script>
const LOCATIONS = {js_data};

const map = L.map('map', {{
  center: [22.3193, 114.1694],
  zoom: 12,
  zoomControl: true,
}});
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
  maxZoom: 18,
}}).addTo(map);

let activeCategory = 'all';
let activeMarkerEl = null;
let currentJobs    = [];
let sortBySalary   = false;

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
  const cat = activeCategory;
  let filtered = cat === 'all' ? [...jobs] : jobs.filter(j => j.label === cat);

  if (sortBySalary) {{
    filtered.sort((a, b) => b.sal_num - a.sal_num);
  }}

  document.getElementById('side-sub').textContent =
    `${{filtered.length}} 个职位` + (cat !== 'all' ? `（${{cat}}）` : '');

  const list = document.getElementById('job-list');
  if (!filtered.length) {{
    list.innerHTML = '<div class="empty">该地区暂无此类职位</div>';
    return;
  }}

  list.innerHTML = filtered.map((j, i) => {{
    const hasSal = j.salary && j.salary !== '薪资面议';
    const salRow = hasSal
      ? `<div class="jc-sal"><span class="jc-sal-icon">💰</span><span class="jc-sal-txt">${{j.salary}}</span></div>`
      : `<div class="jc-sal"><span class="jc-sal-icon">💰</span><span class="jc-sal-none">薪资面议</span></div>`;
    const jdEnc  = encodeURIComponent((j.snippet||'').substring(0,500));
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
          <span class="badge b-cat" style="background:${{j.color}}">${{j.label}}</span>
          <span class="badge b-loc">📍 ${{j.location}}</span>
          ${{j.posted ? `<span class="badge b-dat">🕐 ${{j.posted}}</span>` : ''}}
        </div>
        <div class="jd-tabs">
          <div class="jd-tab on" onclick="switchTab(this,'${{i}}-en')">📄 JD</div>
        </div>
        <div class="jd-panel on" id="p-${{i}}-en">${{j.snippet || '<em>暂无描述</em>'}}</div>
      </div>
      <div class="jc-foot">
        <a class="btn btn-apply" href="${{j.url}}" target="_blank">查看完整JD →</a>
        ${{jdEnc ? `<a class="btn btn-cv" href="resume.html?jd=${{jdEnc}}" target="_blank">✨ 匹配简历</a>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

function switchTab(tab, id) {{
  const card = tab.closest('.jcard');
  card.querySelectorAll('.jd-tab').forEach(t => t.classList.remove('on'));
  card.querySelectorAll('.jd-panel').forEach(p => p.classList.remove('on'));
  tab.classList.add('on');
  const panel = document.getElementById('p-' + id);
  if (panel) panel.classList.add('on');
}}

// ── 分类过滤 ──────────────────────────────────────────────────────────────────
document.getElementById('hdr-filters').addEventListener('click', e => {{
  const tag = e.target.closest('.ftag');
  if (!tag) return;
  activeCategory = tag.dataset.cat;
  document.querySelectorAll('.ftag').forEach(t => t.classList.remove('on'));
  tag.classList.add('on');

  LOCATIONS.forEach((loc, idx) => {{
    const cnt = activeCategory === 'all'
      ? loc.jobs.length
      : loc.jobs.filter(j => j.label === activeCategory).length;
    const el = document.getElementById('mk-' + idx);
    if (el) {{
      el.textContent = cnt;
      el.style.opacity = cnt > 0 ? '1' : '0.25';
    }}
  }});

  if (!document.getElementById('side').classList.contains('closed')) {{
    renderJobs(currentJobs);
  }}
}});
</script>
</body></html>"""

OUTPUT_FILE.write_text(html, encoding="utf-8")
print(f"✅ 地图已生成: {OUTPUT_FILE.resolve()}")
print(f"   {len(loc_groups)} 个地点 · {total_located} 个职位已标注")


if __name__ == "__main__" and "--open" in sys.argv:
    import subprocess
    subprocess.Popen(["open", str(OUTPUT_FILE)])
