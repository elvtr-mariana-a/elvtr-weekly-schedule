"""
Pillow-based renderer for the ELVTR weekly schedule graphic.
All layout is done in base-480px units; the `scale` parameter multiplies everything.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
C = {
    "bg":           (245, 244, 252),
    "header":       (60,  52, 137),
    "week_bar":     (83,  74, 183),
    "white":        (255, 255, 255),
    "card_border":  (206, 203, 246),
    "footer_bg":    (238, 237, 254),
    "footer_text":  (83,  74, 183),
    "elvtr_lbl":    (175, 169, 236),
    "course":       (238, 237, 254),
    "instructor":   (175, 169, 236),
    "week_text":    (206, 203, 246),
    "empty":        (180, 178, 169),
    "title":        (44,  44,  42),
    "time_txt":     (95,  94,  90),
    "note_txt":     (133,  79,  11),
    # day label backgrounds
    "mon_bg":       (83,  74, 183),
    "tue_bg":       (60,  52, 137),
    "wed_bg":       (127, 119, 221),
    "thu_bg":       (38,  33,  92),
    "fri_bg":       (175, 169, 236),
    # day name / date colours
    "mon_nm":       (238, 237, 254),  "mon_dt": (206, 203, 246),
    "tue_nm":       (238, 237, 254),  "tue_dt": (175, 169, 236),
    "wed_nm":       (238, 237, 254),  "wed_dt": (238, 237, 254),
    "thu_nm":       (238, 237, 254),  "thu_dt": (175, 169, 236),
    "fri_nm":       (38,  33,  92),   "fri_dt": (60,  52, 137),
    # event type colours
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
    "divider":      (238, 237, 254),
    # badge colours
    "badge_office_bg":  (29, 158, 117, 31),   # rgba
    "badge_office_bd":  (29, 158, 117),
    "badge_office_txt": (15, 110,  86),
    "badge_ec_bg":      (29, 158, 117, 38),
    "badge_ec_bd":      (29, 158, 117),
    "badge_ec_txt":     (15, 110,  86),
    "ungraded_txt":     (136, 135, 128),
}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
TYPE_LABELS = {
    "class": "CLASS",
    "office": "OFFICE HOURS",
    "due": "ASSIGNMENT DUE",
    "optional": "OPTIONAL",
    "holiday": "HOLIDAY",
}

# ---------------------------------------------------------------------------
# Font loader
# ---------------------------------------------------------------------------
_FONT_DIRS = [
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype/msttcorefonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
]
_FONT_NAMES = {
    "regular": ["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    "bold":    ["arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "italic":  ["ariali.ttf", "Arial Italic.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"],
}

def _find_font(variant: str) -> str | None:
    for d in _FONT_DIRS:
        for name in _FONT_NAMES.get(variant, []):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
    return None

_font_cache: dict[tuple, ImageFont.FreeTypeFont] = {}

def fnt(size: int, variant: str = "regular", scale: int = 1) -> ImageFont.FreeTypeFont:
    key = (size, variant, scale)
    if key not in _font_cache:
        path = _find_font(variant)
        px = size * scale
        if path:
            try:
                _font_cache[key] = ImageFont.truetype(path, px)
            except Exception:
                _font_cache[key] = ImageFont.load_default()
        else:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------
def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 1):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill,
                           outline=outline, width=width)


def _text_height(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> int:
    """Return the pixel height that `text` will occupy when wrapped."""
    lines = _wrap_text(text, font, max_width, draw)
    if not lines:
        return 0
    bbox = draw.textbbox((0, 0), "Ay", font=font)
    line_h = bbox[3] - bbox[1]
    return line_h * len(lines)


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textlength(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _draw_text_wrapped(draw, text, xy, font, fill, max_width):
    x, y = xy
    lines = _wrap_text(text, font, max_width, draw)
    bbox = draw.textbbox((0, 0), "Ay", font=font)
    line_h = bbox[3] - bbox[1]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h
    return y  # returns y after last line


def _draw_badge(draw: ImageDraw.ImageDraw, text: str, xy, font,
                bg_rgba, border_rgb, text_rgb, radius, scale):
    x, y = xy
    tw = draw.textlength(text, font=font)
    bbox = draw.textbbox((0, 0), "Ay", font=font)
    th = bbox[3] - bbox[1]
    pad_x = 6 * scale
    pad_y = 2 * scale
    bx0, by0 = x, y - pad_y
    bx1, by1 = x + tw + pad_x * 2, y + th + pad_y
    # draw background with alpha
    bg_layer = Image.new("RGBA", draw.im.size, (0, 0, 0, 0))
    bg_d = ImageDraw.Draw(bg_layer)
    bg_d.rounded_rectangle([bx0, by0, bx1, by1], radius=radius,
                            fill=bg_rgba, outline=border_rgb, width=scale)
    # composite onto base (assumes base is RGBA)
    draw._image.alpha_composite(bg_layer)
    draw.text((x + pad_x, y), text, font=font, fill=text_rgb)
    return bx1  # right edge of badge


# ---------------------------------------------------------------------------
# Per-event height calculation
# ---------------------------------------------------------------------------
def _event_height(ev: dict, draw: ImageDraw.ImageDraw, content_w: int, scale: int) -> int:
    """Calculate the pixel height of a single event block."""
    s = scale
    line_h_small = draw.textbbox((0, 0), "Ay", font=fnt(10, "regular", s))[3]
    line_h_title = draw.textbbox((0, 0), "Ay", font=fnt(13, "bold",    s))[3]
    line_h_time  = draw.textbbox((0, 0), "Ay", font=fnt(11, "regular", s))[3]

    indent = 13 * s
    h = line_h_small  # type label row

    title_w = content_w - indent
    title_lines = _wrap_text(ev.get("title") or "—", fnt(13, "bold", s), title_w, draw)
    h += line_h_title * len(title_lines)

    if ev.get("type") == "holiday" and ev.get("note"):
        note_lines = _wrap_text(ev["note"], fnt(11, "italic", s), title_w, draw)
        h += line_h_time * len(note_lines)

    has_time_row = (ev.get("timePT") or ev.get("timeET") or
                    (ev.get("type") == "office") or
                    (ev.get("type") == "due" and ev.get("extraCredit")) or
                    (ev.get("type") == "optional" and ev.get("ungraded")))
    if has_time_row:
        h += line_h_time

    return h + 4 * s  # small bottom padding per event


def _day_content_height(events: list, draw: ImageDraw.ImageDraw, content_w: int, scale: int) -> int:
    if not events:
        lh = draw.textbbox((0, 0), "Ay", font=fnt(12, "italic", scale))[3]
        return lh + 16 * scale
    total = 0
    for i, ev in enumerate(events):
        total += _event_height(ev, draw, content_w, scale)
        if i < len(events) - 1:
            total += 5 * scale  # divider gap
    return total + 16 * scale  # top+bottom padding


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------
def render_graphic(data: dict, scale: int = 2) -> Image.Image:
    s = scale
    base_w = 480
    W = base_w * s

    # ---- First pass: measure total height ----
    # We need a scratch surface to measure text
    scratch = Image.new("RGBA", (W, 4000), C["bg"])
    sdraw = ImageDraw.Draw(scratch)

    label_w = 76 * s
    pad_x = 6 * s
    content_w = (base_w - 76 - 12 - 28) * s  # approximate

    header_h = 82 * s
    week_bar_h = 30 * s
    footer_h = 36 * s
    days_pad = 6 * s
    day_gap = 4 * s

    day_heights = []
    for day in DAYS:
        events = data["days"].get(day, [])
        ch = _day_content_height(events, sdraw, content_w, s)
        min_h = 56 * s
        day_heights.append(max(ch, min_h))

    total_days_h = days_pad * 2 + sum(day_heights) + day_gap * (len(DAYS) - 1)
    H = header_h + week_bar_h + total_days_h + footer_h

    # ---- Actual render ----
    img = Image.new("RGBA", (W, H), C["bg"])
    draw = ImageDraw.Draw(img)

    # -- Header --
    draw.rectangle([0, 0, W, header_h], fill=C["header"])
    y = 20 * s
    draw.text((24 * s, y), "ELVTR", font=fnt(10, "bold", s), fill=C["elvtr_lbl"])
    y += draw.textbbox((0, 0), "Ay", font=fnt(10, "bold", s))[3] + 6 * s
    course_name = data.get("name") or "Course Name"
    y = _draw_text_wrapped(draw, course_name, (24 * s, y),
                           fnt(17, "bold", s), C["course"], W - 48 * s)
    y += 3 * s
    instructor = data.get("instructor") or "—"
    draw.text((24 * s, y), f"Instructor: {instructor}",
              font=fnt(12, "regular", s), fill=C["instructor"])

    # -- Week bar --
    wb_y = header_h
    draw.rectangle([0, wb_y, W, wb_y + week_bar_h], fill=C["week_bar"])
    wbl = draw.textbbox((0, 0), "Ay", font=fnt(11, "regular", s))[3]
    draw.text((24 * s, wb_y + (week_bar_h - wbl) // 2),
              _format_week(data.get("weekStart"), data.get("weekEnd")),
              font=fnt(11, "regular", s), fill=C["week_text"])

    # -- Days --
    day_y = header_h + week_bar_h + days_pad
    for idx, day in enumerate(DAYS):
        dh = day_heights[idx]
        events = data["days"].get(day, [])

        # card background
        _draw_rounded_rect(draw, [days_pad, day_y, W - days_pad, day_y + dh],
                           radius=10 * s, fill=C["white"],
                           outline=C["card_border"], width=s)

        slug = day.lower()
        lbl_bg   = C[f"{slug}_bg"]
        name_col = C[f"{slug}_nm"]
        date_col = C[f"{slug}_dt"]

        # left label column (clipped to card with rounded left)
        _draw_rounded_rect(draw,
                           [days_pad, day_y, days_pad + label_w, day_y + dh],
                           radius=10 * s, fill=lbl_bg)
        # cover right half of label rounding with a rectangle
        draw.rectangle([days_pad + label_w // 2, day_y,
                        days_pad + label_w,       day_y + dh], fill=lbl_bg)

        # Day name
        nm_font = fnt(14, "bold", s)
        dt_font = fnt(10, "regular", s)
        nm_h = draw.textbbox((0, 0), "Ay", nm_font)[3]
        dt_h = draw.textbbox((0, 0), "Ay", dt_font)[3]
        total_lbl_h = nm_h + 3 * s + dt_h
        lbl_text_y = day_y + (dh - total_lbl_h) // 2

        draw.text((days_pad + 10 * s, lbl_text_y), day.upper(),
                  font=nm_font, fill=name_col)
        date_str = _get_day_date(data.get("weekStart"), idx)
        draw.text((days_pad + 10 * s, lbl_text_y + nm_h + 3 * s), date_str,
                  font=dt_font, fill=date_col)

        # separator line between label and content
        sep_x = days_pad + label_w
        draw.line([sep_x, day_y + s, sep_x, day_y + dh - s],
                  fill=C["card_border"], width=s)

        # Content
        cx = sep_x + 14 * s
        cy = day_y + 11 * s
        content_right = W - days_pad - 14 * s
        real_content_w = content_right - cx

        if not events:
            draw.text((cx, cy), "No session",
                      font=fnt(12, "italic", s), fill=C["empty"])
        else:
            for ei, ev in enumerate(events):
                if ei > 0:
                    div_y = cy + 2 * s
                    draw.line([cx, div_y, content_right, div_y],
                              fill=C["divider"], width=s)
                    cy += 5 * s

                cy = _draw_event(draw, ev, cx, cy, real_content_w, img, s)

        day_y += dh + day_gap

    # -- Footer --
    foot_y = H - footer_h
    draw.rectangle([0, foot_y, W, H], fill=C["footer_bg"])
    channel = data.get("channel") or "#help"
    foot_txt = f"Posted every Monday · Questions? Drop them in {channel}"
    fw = draw.textlength(foot_txt, font=fnt(10, "regular", s))
    ft_h = draw.textbbox((0, 0), "Ay", font=fnt(10, "regular", s))[3]
    draw.text(((W - fw) // 2, foot_y + (footer_h - ft_h) // 2),
              foot_txt, font=fnt(10, "regular", s), fill=C["footer_text"])

    # Convert to RGB for PNG export
    rgb = Image.new("RGB", img.size, (245, 244, 252))
    rgb.paste(img, mask=img.split()[3])
    return rgb


# ---------------------------------------------------------------------------
# Event renderer
# ---------------------------------------------------------------------------
def _draw_event(draw, ev, cx, cy, content_w, img, s) -> int:
    slug = ev.get("type", "class")
    dot_col  = C.get(f"dot_{slug}", C["dot_class"])
    lbl_col  = C.get(f"lbl_{slug}", C["lbl_class"])
    indent   = 13 * s

    # Dot + type label row
    dot_r = 3 * s
    f10b = fnt(10, "bold", s)
    lh10 = draw.textbbox((0, 0), "Ay", f10b)[3]
    dot_cy = cy + lh10 // 2
    draw.ellipse([cx, dot_cy - dot_r, cx + dot_r * 2, dot_cy + dot_r],
                 fill=dot_col)

    if slug == "class" and ev.get("classNum"):
        type_str = f"CLASS #{ev['classNum']}"
    else:
        type_str = TYPE_LABELS.get(slug, slug.upper())

    draw.text((cx + indent, cy), type_str, font=f10b, fill=lbl_col)
    cy += lh10 + 2 * s

    # Title
    f13b = fnt(13, "bold", s)
    lh13 = draw.textbbox((0, 0), "Ay", f13b)[3]
    title = ev.get("title") or "—"
    title_lines = _wrap_text(title, f13b, content_w - indent, draw)
    for line in title_lines:
        draw.text((cx + indent, cy), line, font=f13b, fill=C["title"])
        cy += lh13
    cy += 2 * s

    # Holiday note
    if slug == "holiday" and ev.get("note"):
        f11i = fnt(11, "italic", s)
        lh11 = draw.textbbox((0, 0), "Ay", f11i)[3]
        note_lines = _wrap_text(ev["note"], f11i, content_w - indent, draw)
        for line in note_lines:
            draw.text((cx + indent, cy), line, font=f11i, fill=C["note_txt"])
            cy += lh11
        cy += 2 * s

    # Time / badge row
    f11 = fnt(11, "regular", s)
    lh11 = draw.textbbox((0, 0), "Ay", f11)[3]

    pt = (ev.get("timePT") or "").strip()
    et = (ev.get("timeET") or "").strip()
    if pt and et:
        time_str = f"{pt} PT / {et} ET"
    elif pt:
        time_str = f"{pt} PT"
    elif et:
        time_str = f"{et} ET"
    else:
        time_str = ""

    has_time_row = bool(
        time_str or
        (slug == "office") or
        (slug == "due" and ev.get("extraCredit")) or
        (slug == "optional" and ev.get("ungraded"))
    )

    if has_time_row:
        tx = cx + indent
        f9b = fnt(9, "bold", s)

        if slug == "due" and ev.get("extraCredit"):
            # Extra Credit badge
            ec_txt = "EXTRA CREDIT"
            ec_bg = (*C["badge_ec_bd"], 38)
            tx = _draw_badge_inline(draw, ec_txt, (tx, cy), f9b,
                                    ec_bg, C["badge_ec_bd"], C["badge_ec_txt"],
                                    10 * s, s, img)
            tx += 6 * s

        if time_str:
            draw.text((tx, cy), time_str, font=f11, fill=C["time_txt"])
            tx += int(draw.textlength(time_str, font=f11)) + 6 * s

        if slug == "office":
            timing = ev.get("officeTiming", "before")
            badge_txt = "⬆ Before class" if timing == "before" else "⬇ After class"
            of_bg = (*C["badge_office_bd"], 31)
            _draw_badge_inline(draw, badge_txt, (tx, cy), f9b,
                               of_bg, C["badge_office_bd"], C["badge_office_txt"],
                               10 * s, s, img)

        if slug == "optional" and ev.get("ungraded"):
            ug_txt = "/ Ungraded"
            draw.text((tx, cy), ug_txt, font=f11, fill=C["ungraded_txt"])

        cy += lh11 + 2 * s

    return cy


def _draw_badge_inline(draw, text, xy, font, bg_rgba, border_rgb, text_rgb, radius, scale, img):
    """Draw a pill badge and return x position after it."""
    x, y = xy
    tw = int(draw.textlength(text, font=font))
    bbox = draw.textbbox((0, 0), "Ay", font=font)
    th = bbox[3] - bbox[1]
    pad_x = 5 * scale
    pad_y = 2 * scale
    bx0, by0 = x, y - pad_y
    bx1, by1 = x + tw + pad_x * 2, y + th + pad_y

    # Draw badge background as overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([bx0, by0, bx1, by1], radius=radius,
                         fill=bg_rgba, outline=border_rgb, width=scale)
    img.alpha_composite(overlay)
    draw.text((x + pad_x, y), text, font=font, fill=text_rgb)
    return bx1


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def _format_week(start_str: str | None, end_str: str | None) -> str:
    if not start_str:
        return "Week of —"
    from datetime import date
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    try:
        s = date.fromisoformat(start_str)
        sm, sd = months[s.month - 1], s.day
        if not end_str:
            return f"Week of {sm} {sd}"
        e = date.fromisoformat(end_str)
        em, ed = months[e.month - 1], e.day
        yr = s.year
        if sm == em:
            return f"Week of {sm} {sd} – {ed}, {yr}"
        return f"Week of {sm} {sd} – {em} {ed}, {yr}"
    except Exception:
        return "Week of —"


def _get_day_date(start_str: str | None, day_index: int) -> str:
    if not start_str:
        return ""
    from datetime import date, timedelta
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    try:
        d = date.fromisoformat(start_str) + timedelta(days=day_index)
        return f"{months[d.month - 1]} {d.day}"
    except Exception:
        return ""
