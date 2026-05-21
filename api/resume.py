"""
秒投 — Resume PDF generator (Vercel Python serverless function)
Adapted from Aurora's generate_resume.py: ReportLab one-page A4 output
with an auto-fit loop (scales font + spacing down until it fits 1 page)
and hanging-indent bullets.
POST JSON resume data -> application/pdf
"""
from http.server import BaseHTTPRequestHandler
import json, base64
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                HRFlowable, Table, TableStyle, Image)
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader

# 中文字体（用于中文姓名）— ReportLab 自带的 CID 字体，无需字体文件
try:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    CJK_FONT = "STSong-Light"
except Exception:
    CJK_FONT = None

PAGE_W, PAGE_H = A4
MARGIN_H  = 20 * mm
FRAME_PAD = 6
PHOTO_W, PHOTO_H = 70, 84

FONTS = {
    "classic": {"reg": "Times-Roman", "bold": "Times-Bold", "ital": "Times-Italic",
                "name": colors.black, "rule": colors.HexColor("#333333")},
    "modern":  {"reg": "Helvetica", "bold": "Helvetica-Bold", "ital": "Helvetica-Oblique",
                "name": colors.HexColor("#15803d"), "rule": colors.HexColor("#16a34a")},
}

# (font_size, spacing_mult, v_margin_mm) — tried in order until 1 page
SCALES = [
    (9.6, 1.00, 16), (9.2, 1.00, 14), (8.8, 0.96, 13), (8.5, 0.92, 12),
    (8.2, 0.88, 11), (7.9, 0.83, 10), (7.6, 0.78, 9), (7.3, 0.74, 8.5),
    (7.0, 0.70, 8),
]


def esc(s):
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _photo_flowable(photo):
    """data-URL -> ReportLab Image (center-cropped to passport ratio), or None."""
    if not photo or not isinstance(photo, str) or not photo.startswith("data:"):
        return None
    try:
        raw = base64.b64decode(photo.split(",", 1)[1])
    except Exception:
        return None
    try:
        from PIL import Image as PILImage
        im = PILImage.open(BytesIO(raw))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        tw, th = im.size
        target = PHOTO_W / PHOTO_H
        if tw / th > target:                 # too wide -> crop sides
            nw = int(th * target)
            x = (tw - nw) // 2
            im = im.crop((x, 0, x + nw, th))
        else:                                # too tall -> crop top/bottom
            nh = int(tw / target)
            y = (th - nh) // 2
            im = im.crop((0, y, tw, y + nh))
        out = BytesIO()
        im.save(out, format="JPEG", quality=88)
        out.seek(0)
        return Image(out, width=PHOTO_W, height=PHOTO_H)
    except Exception:
        try:
            return Image(BytesIO(raw), width=PHOTO_W, height=PHOTO_H)
        except Exception:
            return None


def build_story(data, fs, sp, F):
    """Build a fresh flowable story at the given scale."""
    UW = PAGE_W - 2 * MARGIN_H - 2 * FRAME_PAD

    bw = round(stringWidth("• ", F["reg"], fs * 0.97)) + 1

    name_s = ParagraphStyle("N", fontName=F["bold"], fontSize=fs * 2.0,
        leading=fs * 2.3, textColor=F["name"])
    namezh_s = ParagraphStyle("NZ", fontName=CJK_FONT or F["reg"],
        fontSize=fs * 1.15, leading=fs * 1.5, textColor=colors.HexColor("#333333"),
        spaceBefore=1)
    pos_s = ParagraphStyle("P", fontName=F["ital"], fontSize=fs,
        leading=fs * 1.35, textColor=colors.HexColor("#555555"), spaceBefore=2)
    contact_s = ParagraphStyle("C", fontName=F["reg"], fontSize=fs * 0.92,
        leading=fs * 1.5, textColor=colors.HexColor("#444444"), spaceBefore=3 * sp)
    small_s = ParagraphStyle("SM", fontName=F["reg"], fontSize=fs * 0.85,
        leading=fs * 1.4, textColor=colors.HexColor("#444444"), spaceBefore=2 * sp)
    sec_s = ParagraphStyle("S", fontName=F["bold"], fontSize=fs * 1.05,
        spaceBefore=7 * sp, spaceAfter=2 * sp, letterSpacing=0.7,
        textColor=F["name"])
    body_s = ParagraphStyle("B", fontName=F["reg"], fontSize=fs,
        leading=fs * 1.44, spaceAfter=0)
    body_r_s = ParagraphStyle("BR", fontName=F["reg"], fontSize=fs * 0.92,
        leading=fs * 1.44, alignment=TA_RIGHT, textColor=colors.HexColor("#444444"))
    bul_s = ParagraphStyle("BU", fontName=F["reg"], fontSize=fs * 0.97,
        leading=fs * 1.42, leftIndent=bw, firstLineIndent=-bw, spaceAfter=1.2 * sp)
    sum_s = ParagraphStyle("SU", fontName=F["reg"], fontSize=fs * 0.97,
        leading=fs * 1.5, textColor=colors.HexColor("#1a1a1a"))

    def hr():
        return HRFlowable(width="100%", thickness=0.5, color=F["rule"],
                          spaceAfter=1 * sp, spaceBefore=0)

    def section(title):
        return [Paragraph(esc(title), sec_s), hr()]

    def bul(items):
        return [Paragraph("• " + str(it), bul_s) for it in items if str(it).strip()]

    def row(left_main, left_sub, right_top, right_bot):
        sub_fs = round(fs * 0.93, 1)
        lh = "<b>%s</b>" % esc(left_main)
        if left_sub:
            lh += '<br/><font size="%s">%s</font>' % (sub_fs, esc(left_sub))
        rh = esc(right_top)
        if right_bot:
            rh += "<br/>" + esc(right_bot)
        t = Table([[Paragraph(lh, body_s), Paragraph(rh, body_r_s)]],
                  colWidths=[UW * 0.64, UW * 0.36])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * sp),
        ]))
        return t

    S = []

    # ── Header (name block + optional photo) ──────────────────────────────
    head = [Paragraph(esc(data.get("name", "Your Name")), name_s)]
    if data.get("nameZh"):
        head.append(Paragraph(esc(data["nameZh"]), namezh_s))
    if data.get("position"):
        head.append(Paragraph(esc(data["position"]), pos_s))
    contacts = [c for c in (data.get("contacts") or []) if str(c).strip()]
    if contacts:
        head.append(Paragraph("&#160;&#160;|&#160;&#160;".join(esc(c) for c in contacts),
                              contact_s))
    particulars = data.get("particulars") or []
    if particulars:
        head.append(Paragraph("&#160;&#160;&#160;".join(
            "<b>%s:</b> %s" % (esc(p[0]), esc(p[1])) for p in particulars), small_s))

    photo = _photo_flowable(data.get("photo"))
    if photo:
        ht = Table([[head, photo]], colWidths=[UW - PHOTO_W - 10, PHOTO_W + 10])
        ht.setStyle(TableStyle([
            ("VALIGN", (0, 0), (0, 0), "TOP"),
            ("VALIGN", (1, 0), (1, 0), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        S.append(ht)
    else:
        S += head
    S.append(HRFlowable(width="100%", thickness=1, color=colors.black,
                        spaceBefore=5 * sp, spaceAfter=4 * sp))

    # ── Objective ─────────────────────────────────────────────────────────
    if data.get("objective"):
        S += section("OBJECTIVE")
        S.append(Paragraph(esc(data["objective"]), sum_s))

    # ── Education ─────────────────────────────────────────────────────────
    edu = data.get("education") or []
    if edu:
        S += section("EDUCATION")
        for ed in edu:
            S.append(Spacer(1, 3 * sp))
            org = ed.get("org", "")
            if ed.get("extra"):
                org = (org + "  |  " + ed["extra"]).strip(" |")
            S.append(row(ed.get("title", ""), org, ed.get("dates", ""), ""))
            S += bul(ed.get("bullets") or [])

    # ── Awards ────────────────────────────────────────────────────────────
    awards = data.get("awards") or []
    if awards:
        S += section("AWARDS & ACHIEVEMENTS")
        for aw in awards:
            S.append(Spacer(1, 2 * sp))
            S.append(row(aw.get("title", ""), "", aw.get("dates", ""), ""))

    # ── Experience ────────────────────────────────────────────────────────
    exp = data.get("experience") or []
    if exp:
        S += section("WORK & INTERNSHIP EXPERIENCE")
        for ex in exp:
            S.append(Spacer(1, 3 * sp))
            S.append(row(ex.get("org", "") or ex.get("title", ""),
                         ex.get("title", "") if ex.get("org") else "",
                         ex.get("dates", ""), ex.get("location", "")))
            S += bul(ex.get("bullets") or [])

    # ── Skills ────────────────────────────────────────────────────────────
    skills = data.get("skills") or []
    if skills:
        S += section("SKILLS & QUALIFICATIONS")
        S += bul(["<b>%s:</b> %s" % (esc(s[0]), esc(s[1])) for s in skills
                  if s and str(s[1]).strip()])

    # ── Extracurricular ───────────────────────────────────────────────────
    extra = data.get("extracurricular") or []
    if extra:
        S += section("EXTRACURRICULAR & VOLUNTEER ACTIVITIES")
        for xt in extra:
            S.append(Spacer(1, 2 * sp))
            S.append(row(xt.get("title", ""), xt.get("desc", ""),
                         xt.get("dates", ""), ""))

    # ── Footer ────────────────────────────────────────────────────────────
    foot = data.get("footer") or {}
    bits = []
    if foot.get("salary"):
        bits.append("Expected Salary: " + esc(foot["salary"]))
    if foot.get("availability"):
        bits.append("Availability: " + esc(foot["availability"]))
    foot_left = "&#160;&#160;|&#160;&#160;".join(bits)
    foot_s = ParagraphStyle("F", fontName=F["reg"], fontSize=fs * 0.85,
        leading=fs * 1.3, textColor=colors.HexColor("#444444"))
    foot_r = ParagraphStyle("FR", parent=foot_s, alignment=TA_RIGHT)
    S.append(Spacer(1, 9 * sp))
    S.append(HRFlowable(width="100%", thickness=0.5,
                        color=colors.HexColor("#cccccc"), spaceAfter=4 * sp))
    ft = Table([[Paragraph(foot_left, foot_s),
                 Paragraph("<i>References available upon request</i>", foot_r)]],
               colWidths=[UW * 0.6, UW * 0.4])
    ft.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    S.append(ft)
    return S


def _render(data, fs, sp, mv_mm, F):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=MARGIN_H, rightMargin=MARGIN_H,
        topMargin=mv_mm * mm, bottomMargin=mv_mm * mm)
    doc.build(build_story(data, fs, sp, F))
    return buf.getvalue()


def generate_pdf(data):
    F = FONTS["modern" if data.get("template") == "modern" else "classic"]
    for fs, sp, mv_mm in SCALES:
        pdf = _render(data, fs, sp, mv_mm, F)
        if len(PdfReader(BytesIO(pdf)).pages) == 1:
            return pdf
    # fallback: tightest scale even if >1 page
    fs, sp, mv_mm = SCALES[-1]
    return _render(data, fs, sp, mv_mm, F)


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            pdf = generate_pdf(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="resume.pdf"')
            self._cors()
            self.end_headers()
            self.wfile.write(pdf)
        except Exception as ex:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(ex)}).encode())


if __name__ == "__main__":
    sample = {
        "name": "CHAN, Mei Ki", "nameZh": "陳美琪",
        "position": "Management Trainee / PR Officer",
        "contacts": ["+852 9123 4567", "meiki@gmail.com", "Kowloon, Hong Kong"],
        "particulars": [["Date of Birth", "01/01/2001"], ["Gender", "Female"]],
        "objective": "A highly motivated graduate with a BA in English and MA in "
                     "Philosophy, seeking to contribute strong analytical and "
                     "communication skills to a dynamic organisation.",
        "education": [
            {"title": "Master of Arts in Philosophy", "org": "The University of Hong Kong",
             "extra": "Distinction", "dates": "Sep 2022 – Jul 2024",
             "bullets": ["Thesis on applied ethics; relevant modules in logic and policy"]},
            {"title": "Bachelor of Arts in English", "org": "City University of Hong Kong",
             "dates": "Sep 2018 – Jul 2022", "bullets": []},
        ],
        "awards": [{"title": "Dean's List", "dates": "HKU · 2023"}],
        "experience": [
            {"title": "PR Intern", "org": "ABC Communications", "dates": "Jun–Aug 2023",
             "bullets": ["Drafted bilingual press releases and media materials",
                         "Coordinated 5+ events with 100+ attendees"]},
        ],
        "skills": [["Languages", "English, Cantonese, Mandarin"],
                   ["IT Skills", "MS Office, Adobe CC"]],
        "extracurricular": [{"title": "President, Debate Society", "dates": "2021–2022",
                             "desc": "Led inter-varsity competitions"}],
        "footer": {"salary": "HK$18,000/month", "availability": "Immediately"},
        "template": "classic",
    }
    out = generate_pdf(sample)
    with open("/tmp/test_resume.pdf", "wb") as f:
        f.write(out)
    pages = len(PdfReader(BytesIO(out)).pages)
    print("✓ /tmp/test_resume.pdf  (%d byte, %d page)" % (len(out), pages))
