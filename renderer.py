"""
Pillow-based renderer for the ELVTR weekly schedule graphic.
Call render_graphic(data, scale=1, scheme="Purple") -> PIL Image.
"""
from __future__ import annotations
import os
import re
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Colour palette — base (event/text colours, never change with scheme)
# ---------------------------------------------------------------------------
BASE_C = {
    "white":        (255, 255, 255),
    "title":        (44,  44,  42),
    "time_txt":     (95,  94,  90),
    "note_txt":     (133,  79,  11),
    "empty":        (180, 178, 169),
    # event type
    "dot_class":    (83,  74, 183),
    "dot_office":   (29, 158, 117),
    "dot_due":      (186, 117,  23),
    "dot_optional": (136, 135, 128),
    "dot_holiday":  (201,  64,  64),
    "lbl_class":    (83,  74, 183),
    "lbl_office":   (15, 110,  86),
    "lbl_due":      (133,  79,  11),
    "lbl_optional": (95,  94,  90),
    "lbl_holiday":  (163,  45,  45),
    "divider":      (230, 228, 248),
    # badge
    "badge_office_bg":  (29, 158, 117, 30),
    "badge_office_bd":  (29, 158, 117),
    "badge_office_txt": (15, 110,  86),
    "badge_ec_bg":      (29, 158, 117, 38),
    "badge_ec_bd":      (29, 158, 117),
    "badge_ec_txt":     (15, 110,  86),
    "ungraded_txt":     (136, 135, 128),
}

# ---------------------------------------------------------------------------
# Colour schemes (chrome / decoration colours)
# ---------------------------------------------------------------------------
SCHEMES = {
    "Purple": {
        "bg":          (245, 244, 252),
        "header":      (60,  52, 137),
        "week_bar":    (83,  74, 183),
        "elvtr_lbl":   (175, 169, 236),
        "course_col":  (238, 237, 254),
        "instr_col":   (175, 169, 236),
        "week_text":   (206, 203, 246),
        "card_border": (206, 203, 246),
        "footer_bg":   (238, 237, 254),
        "footer_text": (83,  74, 183),
        "mon_bg": (83,74,183),  "mon_nm":(238,237,254), "mon_dt":(206,203,246),
        "tue_bg": (60,52,137),  "tue_nm":(238,237,254), "tue_dt":(175,169,236),
        "wed_bg": (127,119,221),"wed_nm":(238,237,254), "wed_dt":(238,237,254),
        "thu_bg": (38,33,92),   "thu_nm":(238,237,254), "thu_dt":(175,169,236),
        "fri_bg": (175,169,236),"fri_nm":(38,33,92),    "fri_dt":(60,52,137),
    },
    "Blue": {
        "bg":          (240, 246, 255),
        "header":      (15,  50, 115),
        "week_bar":    (28,  78, 158),
        "elvtr_lbl":   (155, 190, 235),
        "course_col":  (228, 240, 255),
        "instr_col":   (155, 190, 235),
        "week_text":   (185, 214, 250),
        "card_border": (175, 210, 248),
        "footer_bg":   (218, 234, 255),
        "footer_text": (28,  78, 158),
        "mon_bg": (28,78,158),  "mon_nm":(228,240,255), "mon_dt":(185,214,250),
        "tue_bg": (15,50,115),  "tue_nm":(228,240,255), "tue_dt":(155,190,235),
        "wed_bg": (58,118,210), "wed_nm":(228,240,255), "wed_dt":(228,240,255),
        "thu_bg": (8, 30, 75),  "thu_nm":(228,240,255), "thu_dt":(155,190,235),
        "fri_bg": (155,190,235),"fri_nm":(8,30,75),     "fri_dt":(15,50,115),
    },
    "Green": {
        "bg":          (240, 250, 244),
        "header":      (14,  72,  52),
        "week_bar":    (24, 118,  82),
        "elvtr_lbl":   (135, 208, 170),
        "course_col":  (218, 248, 230),
        "instr_col":   (135, 208, 170),
        "week_text":   (165, 228, 192),
        "card_border": (160, 222, 188),
        "footer_bg":   (205, 242, 222),
        "footer_text": (24, 118,  82),
        "mon_bg": (24,118,82),  "mon_nm":(218,248,230), "mon_dt":(165,228,192),
        "tue_bg": (14,72,52),   "tue_nm":(218,248,230), "tue_dt":(135,208,170),
        "wed_bg": (52,168,108), "wed_nm":(218,248,230), "wed_dt":(218,248,230),
        "thu_bg": (8, 45, 32),  "thu_nm":(218,248,230), "thu_dt":(135,208,170),
        "fri_bg": (135,208,170),"fri_nm":(8,45,32),     "fri_dt":(14,72,52),
    },
    "Grayscale": {
        "bg":          (248, 248, 248),
        "header":      (32,  32,  32),
        "week_bar":    (66,  66,  66),
        "elvtr_lbl":   (175, 175, 175),
        "course_col":  (242, 242, 242),
        "instr_col":   (175, 175, 175),
        "week_text":   (205, 205, 205),
        "card_border": (205, 205, 205),
        "footer_bg":   (232, 232, 232),
        "footer_text": (66,  66,  66),
        "mon_bg": (66,66,66),   "mon_nm":(242,242,242), "mon_dt":(205,205,205),
        "tue_bg": (32,32,32),   "tue_nm":(242,242,242), "tue_dt":(175,175,175),
        "wed_bg": (108,108,108),"wed_nm":(242,242,242), "wed_dt":(242,242,242),
        "thu_bg": (18,18,18),   "thu_nm":(242,242,242), "thu_dt":(175,175,175),
        "fri_bg": (175,175,175),"fri_nm":(18,18,18),    "fri_dt":(32,32,32),
    },
}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
TYPE_LABELS = {
    "class":    "CLASS",
    "office":   "OFFICE HOURS",
    "due":      "ASSIGNMENT DUE",
    "optional": "OPTIONAL",
    "holiday":  "HOLIDAY",
}

# ---------------------------------------------------------------------------
# Font management
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS_DIR = os.path.join(_HERE, "fonts")

_FONT_DIRS = [
    _FONTS_DIR,                                          # bundled / downloaded
    "C:/Windows/Fonts",                                  # Windows
    "/usr/share/fonts/truetype/dejavu",                  # Ubuntu / Streamlit Cloud
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/ubuntu",
    "/usr/share/fonts/truetype/freefont",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/Library/Fonts",                                    # macOS
    "/System/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
]
_FONT_NAMES = {
    "regular": ["DMSans-Regular.ttf", "arial.ttf", "Arial.ttf",
                "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
                "Ubuntu-R.ttf", "FreeSans.ttf"],
    "bold":    ["DMSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf",
                "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf",
                "Ubuntu-B.ttf", "FreeSansBold.ttf"],
    "italic":  ["DMSans-Italic.ttf", "ariali.ttf", "Arial Italic.ttf",
                "DejaVuSans-Oblique.ttf", "LiberationSans-Italic.ttf",
                "Ubuntu-RI.ttf", "FreeSansOblique.ttf"],
}

def _try_download_dmsans():
    """Download DM Sans TTFs to ./fonts/ on first run (silent if offline)."""
    os.makedirs(_FONTS_DIR, exist_ok=True)
    targets = [
        ("DMSans-Regular.ttf", "DM+Sans:wght@400"),
        ("DMSans-Bold.ttf",    "DM+Sans:wght@700"),
        ("DMSans-Italic.ttf",  "DM+Sans:ital,wght@1,400"),
    ]
    # Old IE UA forces Google Fonts to return TTF (not WOFF2)
    headers = {"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"}
    for filename, family in targets:
        dest = os.path.join(_FONTS_DIR, filename)
        if os.path.exists(dest):
            continue
        try:
            css_url = f"https://fonts.googleapis.com/css?family={family}"
            req = urllib.request.Request(css_url, headers=headers)
            css = urllib.request.urlopen(req, timeout=8).read().decode("utf-8")
            m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
            if m:
                urllib.request.urlretrieve(m.group(1), dest)
        except Exception:
            pass   # offline or blocked — fall back to system fonts

_try_download_dmsans()

def _find_font(variant: str) -> str | None:
    for d in _FONT_DIRS:
        for name in _FONT_NAMES.get(variant, []):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None

_font_cache: dict = {}

def fnt(size: int, variant: str = "regular", scale: int = 1):
    key = (size, variant, scale)
    if key in _font_cache:
        return _font_cache[key]
    path = _find_font(variant)
    px = size * scale
    if path:
        try:
            _font_cache[key] = ImageFont.truetype(path, px)
            return _font_cache[key]
        except Exception:
            pass
    # Pillow 10+ supports size on the default font
    try:
        _font_cache[key] = ImageFont.load_default(size=px)
    except TypeError:
        _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    if not text:
        return [""]
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]

def _lh(draw, font) -> int:
    return draw.textbbox((0, 0), "Ay", font=font)[3]

def _draw_wrapped(draw, text, xy, font, fill, max_w) -> int:
    x, y = xy
    h = _lh(draw, font)
    for line in _wrap(text, font, max_w, draw):
        draw.text((x, y), line, font=font, fill=fill)
        y += h
    return y

def _rounded_rect(draw, xy, r, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def _badge(draw, img, text, xy, font, bg_rgba, border_rgb, text_rgb, r, s):
    """Draw a pill badge; return right-edge x."""
    x, y = xy
    tw = int(draw.textlength(text, font=font))
    th = _lh(draw, font)
    px, py = 6 * s, 2 * s
    bx0, by0 = x, y - py
    bx1, by1 = x + tw + px * 2, y + th + py
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([bx0, by0, bx1, by1], radius=r,
                         fill=bg_rgba, outline=border_rgb, width=s)
    img.alpha_composite(overlay)
    draw.text((x + px, y), text, font=font, fill=text_rgb)
    return bx1

# ---------------------------------------------------------------------------
# Height calculation
# ---------------------------------------------------------------------------
def _event_h(ev: dict, draw, cw: int, s: int) -> int:
    indent = 14 * s
    h  = _lh(draw, fnt(10, "bold",    s)) + 4 * s   # type label
    h += _lh(draw, fnt(13, "bold",    s)) * len(    # title lines
            _wrap(ev.get("title") or "-", fnt(13, "bold", s), cw - indent, draw))
    h += 3 * s
    if ev.get("type") == "holiday" and ev.get("note"):
        h += _lh(draw, fnt(11, "italic", s)) + 2 * s
    has_time = (ev.get("timePT") or ev.get("timeET") or
                ev.get("type") == "office" or
                (ev.get("type") == "due"      and ev.get("extraCredit")) or
                (ev.get("type") == "optional" and ev.get("ungraded")))
    if has_time:
        h += _lh(draw, fnt(11, "regular", s)) + 3 * s
    return h

def _day_h(events, draw, cw, s) -> int:
    pad = 14 * s
    if not events:
        return _lh(draw, fnt(12, "italic", s)) + pad * 2
    total = pad
    for i, ev in enumerate(events):
        total += _event_h(ev, draw, cw, s)
        if i < len(events) - 1:
            total += 8 * s   # divider gap
    total += pad
    return max(total, 60 * s)

# ---------------------------------------------------------------------------
# Event renderer
# ---------------------------------------------------------------------------
def _draw_event(draw, img, ev, cx, cy, cw, s, c) -> int:
    slug    = ev.get("type", "class")
    dot_col = c.get(f"dot_{slug}", c["dot_class"])
    lbl_col = c.get(f"lbl_{slug}", c["lbl_class"])
    indent  = 14 * s

    # ── Type label + dot ──────────────────────────────────────────────────
    f10b = fnt(10, "bold", s)
    lh10 = _lh(draw, f10b)
    dot_r = 3 * s
    draw.ellipse([cx, cy + lh10 // 2 - dot_r,
                  cx + dot_r * 2, cy + lh10 // 2 + dot_r], fill=dot_col)
    if slug == "class" and ev.get("classNum"):
        type_str = f"CLASS #{ev['classNum']}"
    else:
        type_str = TYPE_LABELS.get(slug, slug.upper())
    draw.text((cx + indent, cy), type_str, font=f10b, fill=lbl_col)
    cy += lh10 + 4 * s

    # ── Title ─────────────────────────────────────────────────────────────
    f13b = fnt(13, "bold", s)
    lh13 = _lh(draw, f13b)
    for line in _wrap(ev.get("title") or "-", f13b, cw - indent, draw):
        draw.text((cx + indent, cy), line, font=f13b, fill=c["title"])
        cy += lh13
    cy += 3 * s

    # ── Holiday note ──────────────────────────────────────────────────────
    if slug == "holiday" and ev.get("note"):
        f11i = fnt(11, "italic", s)
        lh11 = _lh(draw, f11i)
        for line in _wrap(ev["note"], f11i, cw - indent, draw):
            draw.text((cx + indent, cy), line, font=f11i, fill=c["note_txt"])
            cy += lh11
        cy += 2 * s

    # ── Time / badge row ──────────────────────────────────────────────────
    f11  = fnt(11, "regular", s)
    f9b  = fnt(9,  "bold",    s)
    lh11 = _lh(draw, f11)

    pt = (ev.get("timePT") or "").strip()
    et = (ev.get("timeET") or "").strip()
    time_str = (f"{pt} PT / {et} ET" if pt and et
                else (f"{pt} PT" if pt else (f"{et} ET" if et else "")))

    has_time = bool(time_str or slug == "office" or
                    (slug == "due"      and ev.get("extraCredit")) or
                    (slug == "optional" and ev.get("ungraded")))

    if has_time:
        tx = cx + indent
        if slug == "due" and ev.get("extraCredit"):
            tx = _badge(draw, img, "EXTRA CREDIT", (tx, cy), f9b,
                        (*c["badge_ec_bd"], 38),
                        c["badge_ec_bd"], c["badge_ec_txt"], 10 * s, s) + 6 * s
        if time_str:
            draw.text((tx, cy), time_str, font=f11, fill=c["time_txt"])
            tx += int(draw.textlength(time_str, font=f11)) + 6 * s
        if slug == "office":
            # plain ASCII-safe label — no emoji arrows
            timing = ev.get("officeTiming", "before")
            badge_txt = "Before class" if timing == "before" else "After class"
            _badge(draw, img, badge_txt, (tx, cy), f9b,
                   (*c["badge_office_bd"], 30),
                   c["badge_office_bd"], c["badge_office_txt"], 10 * s, s)
        if slug == "optional" and ev.get("ungraded"):
            draw.text((tx, cy), "/ Ungraded", font=f11, fill=c["ungraded_txt"])
        cy += lh11 + 3 * s

    return cy

# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------
def render_graphic(data: dict, scale: int = 1, scheme: str = "Purple") -> Image.Image:
    s = scale
    W = 480 * s
    c = {**BASE_C, **SCHEMES.get(scheme, SCHEMES["Purple"])}

    # ── First pass: measure heights ──────────────────────────────────────
    scratch = Image.new("RGBA", (W, 4000), c["bg"])
    sdraw   = ImageDraw.Draw(scratch)

    label_w  = 76  * s
    day_pad  = 6   * s
    day_gap  = 4   * s
    cx0      = day_pad + label_w + 14 * s        # left edge of content
    cw       = W - cx0 - 14 * s                  # content width

    header_h  = 88 * s
    week_h    = 30 * s
    footer_h  = 36 * s
    day_hs    = [max(_day_h(data["days"].get(d, []), sdraw, cw, s), 58 * s)
                 for d in DAYS]
    total_H   = (header_h + week_h + footer_h
                 + day_pad * 2 + sum(day_hs) + day_gap * (len(DAYS) - 1))

    # ── Actual canvas ────────────────────────────────────────────────────
    img  = Image.new("RGBA", (W, total_H), c["bg"])
    draw = ImageDraw.Draw(img)

    # ── Header ───────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, header_h], fill=c["header"])
    y = 22 * s
    draw.text((24 * s, y), "ELVTR", font=fnt(10, "bold", s), fill=c["elvtr_lbl"])
    y += _lh(draw, fnt(10, "bold", s)) + 7 * s
    y = _draw_wrapped(draw, data.get("name") or "Course Name",
                      (24 * s, y), fnt(17, "bold", s), c["course_col"], W - 48 * s)
    y += 4 * s
    draw.text((24 * s, y),
              f"Instructor: {data.get('instructor') or '-'}",
              font=fnt(12, "regular", s), fill=c["instr_col"])

    # ── Week bar ─────────────────────────────────────────────────────────
    wb_y = header_h
    draw.rectangle([0, wb_y, W, wb_y + week_h], fill=c["week_bar"])
    f11  = fnt(11, "regular", s)
    lh11 = _lh(draw, f11)
    week_label = _format_week(data.get("weekStart"), data.get("weekEnd"))
    draw.text((24 * s, wb_y + (week_h - lh11) // 2),
              week_label, font=f11, fill=c["week_text"])

    # ── Days ─────────────────────────────────────────────────────────────
    day_y = header_h + week_h + day_pad
    for idx, day in enumerate(DAYS):
        dh     = day_hs[idx]
        events = data["days"].get(day, [])
        slug   = day.lower()

        # card
        _rounded_rect(draw,
                      [day_pad, day_y, W - day_pad, day_y + dh],
                      r=10 * s, fill=c["white"],
                      outline=c["card_border"], width=s)

        # left label
        lbl_bg = c[f"{slug}_bg"]
        _rounded_rect(draw,
                      [day_pad, day_y, day_pad + label_w, day_y + dh],
                      r=10 * s, fill=lbl_bg)
        # mask the right-side rounded corners of the label column
        draw.rectangle([day_pad + label_w // 2, day_y,
                        day_pad + label_w - 1,  day_y + dh], fill=lbl_bg)

        nm_f = fnt(14, "bold",    s)
        dt_f = fnt(10, "regular", s)
        lh_nm, lh_dt = _lh(draw, nm_f), _lh(draw, dt_f)
        block_h = lh_nm + 4 * s + lh_dt
        ty = day_y + (dh - block_h) // 2
        draw.text((day_pad + 10 * s, ty),
                  day.upper(), font=nm_f, fill=c[f"{slug}_nm"])
        draw.text((day_pad + 10 * s, ty + lh_nm + 4 * s),
                  _get_date(data.get("weekStart"), idx),
                  font=dt_f, fill=c[f"{slug}_dt"])

        # separator line
        sx = day_pad + label_w
        draw.line([sx, day_y + s, sx, day_y + dh - s],
                  fill=c["card_border"], width=s)

        # content
        cy   = day_y + 14 * s
        cont_x = sx + 14 * s
        if not events:
            draw.text((cont_x, cy), "No session",
                      font=fnt(12, "italic", s), fill=c["empty"])
        else:
            for ei, ev in enumerate(events):
                if ei > 0:
                    dy = cy + 3 * s
                    draw.line([cont_x, dy, W - day_pad - 14 * s, dy],
                              fill=c["divider"], width=s)
                    cy += 8 * s
                cy = _draw_event(draw, img, ev, cont_x, cy, cw, s, c)

        day_y += dh + day_gap

    # ── Footer ───────────────────────────────────────────────────────────
    foot_y = total_H - footer_h
    draw.rectangle([0, foot_y, W, total_H], fill=c["footer_bg"])
    channel = data.get("channel") or "#help"
    foot_txt = f"Posted every Monday  ·  Questions? Drop them in {channel}"
    fw  = draw.textlength(foot_txt, font=fnt(10, "regular", s))
    ft_h = _lh(draw, fnt(10, "regular", s))
    draw.text(((W - fw) // 2, foot_y + (footer_h - ft_h) // 2),
              foot_txt, font=fnt(10, "regular", s), fill=c["footer_text"])

    # Flatten RGBA → RGB
    out = Image.new("RGB", img.size, c["bg"][:3])
    out.paste(img, mask=img.split()[3])
    return out

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def _format_week(start: str | None, end: str | None) -> str:
    if not start:
        return "Week of -"
    from datetime import date
    MO = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    try:
        s = date.fromisoformat(start)
        sm, sd = MO[s.month - 1], s.day
        if not end:
            return f"Week of {sm} {sd}"
        e = date.fromisoformat(end)
        em, ed, yr = MO[e.month - 1], e.day, s.year
        # Use plain ASCII hyphen – avoids glyph-missing boxes on some fonts
        return (f"Week of {sm} {sd} - {ed}, {yr}" if sm == em
                else f"Week of {sm} {sd} - {em} {ed}, {yr}")
    except Exception:
        return "Week of -"

def _get_date(start: str | None, idx: int) -> str:
    if not start:
        return ""
    from datetime import date, timedelta
    MO = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    try:
        d = date.fromisoformat(start) + timedelta(days=idx)
        return f"{MO[d.month - 1]} {d.day}"
    except Exception:
        return ""
