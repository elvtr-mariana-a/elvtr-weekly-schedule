"""
ELVTR Weekly Schedule Generator — Streamlit app
"""
import io
import re
import base64
import uuid
import streamlit as st
from datetime import date, timedelta
from renderer import render_graphic

st.set_page_config(
    page_title="ELVTR Schedule Generator",
    page_icon="📅",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS overrides
# ---------------------------------------------------------------------------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f0e1a; }
[data-testid="stSidebar"] { display: none; }
section[data-testid="stMain"] > div:first-child { padding-top: 2.5rem !important; }
h1, h2, h3 { color: #e8e6f8 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
EVENT_TYPES = ["class", "office", "due", "optional", "noclass"]
TYPE_LABELS = {
    "class":    "Class",
    "office":   "Office Hours",
    "due":      "Assignment Due",
    "optional": "Optional",
    "noclass":  "No Class",
}
NOCLASS_TYPES = ["Federal Holiday", "Bank Holiday", "Instructor Day Off"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CLASS_TAGS = ["Guest Speaker", "Workshop", "Case Study"]

def _blank_event(etype: str = "class") -> dict:
    return {
        "id":              str(uuid.uuid4()),
        "type":            etype,
        "title":           "",
        "classNum":        "",
        "tags":            [],        # class-only: Guest Speaker / Workshop / Case Study
        "officeTiming":    "before",
        "officeCancelled": False,
        "extraCredit":     False,
        "ungraded":        False,
        "noClassType":     NOCLASS_TYPES[0],
        "note":            "",
        "timePT":          "",
        "timeET":          "",
        "timeUK":          "",
    }

def _init_event_widgets(ev: dict):
    """Seed session-state widget keys the first time an event is created."""
    eid = ev["id"]
    defaults = {
        f"title_{eid}": ev["title"],
        f"cls_{eid}":   ev["classNum"],
        f"note_{eid}":  ev["note"],
        f"pt_{eid}":    ev["timePT"],
        f"et_{eid}":    ev["timeET"],
        f"uk_{eid}":    ev.get("timeUK", ""),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def _preview_html(img) -> str:
    """Return an <img> tag embedding the image as base64 at exactly 480 px."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'width="480" style="width:480px;max-width:100%;'
        f'border-radius:8px;display:block;" />'
    )

# ---------------------------------------------------------------------------
# Session-state bootstrap
# ---------------------------------------------------------------------------
SCHEMES = ["Purple", "Blue", "Green", "Grayscale"]

for _k, _v in [
    ("events",      {d: [] for d in DAYS}),
    ("course",      ""),
    ("instructor",  ""),
    ("channel",     "#help"),
    ("footer_line", ""),
    ("week_start",  None),
    ("scheme",      "Purple"),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Seed widget state for any already-saved events (page refresh / rerun)
for _d in DAYS:
    for _ev in st.session_state.events[_d]:
        _init_event_widgets(_ev)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
left, right = st.columns([5, 6], gap="large")

# ============================================================
# LEFT — Form
# ============================================================
with left:
    st.markdown("### Course details")

    st.session_state.course = st.text_input(
        "Course name", value=st.session_state.course,
        placeholder="e.g. Fantasy Writing", key="inp_course",
    )
    st.session_state.instructor = st.text_input(
        "Instructor", value=st.session_state.instructor,
        placeholder="e.g. Zoraida Córdova", key="inp_instructor",
    )
    st.session_state.channel = st.text_input(
        "Discord help channel", value=st.session_state.channel,
        placeholder="e.g. #help", key="inp_channel",
    )
    st.session_state.footer_line = st.text_input(
        "Footer text (optional)",
        value=st.session_state.footer_line,
        placeholder="Leave blank to auto-generate from channel name",
        key="inp_footer",
    )

    st.markdown("---")
    st.markdown("### Colour scheme")
    scheme_choice = st.radio(
        "Scheme", SCHEMES,
        index=SCHEMES.index(st.session_state.scheme),
        horizontal=True,
        label_visibility="collapsed",
        key="inp_scheme",
    )
    st.session_state.scheme = scheme_choice

    st.markdown("---")
    st.markdown("### Week")

    raw_start = st.date_input("Start date",
                              value=st.session_state.week_start,
                              key="inp_week_start")

    # Snap start → Monday of that week; end date (Friday) is derived, not entered
    if raw_start and raw_start != st.session_state.week_start:
        mon = raw_start - timedelta(days=raw_start.weekday())
        st.session_state.week_start = mon
        st.rerun()
    elif raw_start:
        st.session_state.week_start = raw_start

    st.markdown("---")
    st.markdown("### Schedule")

    # ── Day blocks ────────────────────────────────────────────────────────
    for day in DAYS:
        with st.expander(day, expanded=True):
            events = st.session_state.events[day]
            action = None   # ("delete" | "up" | "down", index)

            for i, ev in enumerate(events):
                eid = ev["id"]
                _init_event_widgets(ev)   # no-op if already seeded

                st.markdown("<hr style='border-color:#2e2b4a;margin:4px 0 8px'>",
                            unsafe_allow_html=True)

                # ── Header row: type | ▲ | ▼ | ✕ ──────────────────────
                c_type, c_up, c_down, c_del = st.columns([5, 1, 1, 1])

                with c_type:
                    new_type = st.selectbox(
                        "Type", EVENT_TYPES,
                        index=EVENT_TYPES.index(ev["type"]),
                        format_func=lambda t: TYPE_LABELS[t],
                        key=f"type_{eid}",
                    )
                with c_up:
                    st.markdown("<div style='margin-top:26px'>", unsafe_allow_html=True)
                    if st.button("▲", key=f"up_{eid}", disabled=(i == 0), help="Move up"):
                        action = ("up", i)
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_down:
                    st.markdown("<div style='margin-top:26px'>", unsafe_allow_html=True)
                    if st.button("▼", key=f"dn_{eid}",
                                 disabled=(i == len(events) - 1), help="Move down"):
                        action = ("down", i)
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_del:
                    st.markdown("<div style='margin-top:26px'>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_{eid}", help="Remove"):
                        action = ("delete", i)
                    st.markdown("</div>", unsafe_allow_html=True)

                # ── Type change → auto-fill office title ─────────────────
                if new_type != ev["type"]:
                    ev["type"] = new_type
                    if new_type == "office" and not st.session_state.get(f"title_{eid}", "").strip():
                        _parts = (st.session_state.instructor or "").split()
                        first  = _parts[0] if _parts else "Instructor"
                        st.session_state[f"title_{eid}"] = f"Open Q&A with {first}"

                etype = ev["type"]

                # ── Title (reads/writes via session-state key) ───────────
                # We don't pass value= here so Streamlit uses the key's stored value
                ev["title"] = st.text_input(
                    "Title",
                    placeholder="Session title…",
                    key=f"title_{eid}",
                )

                # ── Class # + tags ──────────────────────────────────────
                if etype == "class":
                    ev["classNum"] = st.text_input(
                        "Class #", placeholder="e.g. 5",
                        key=f"cls_{eid}",
                    )
                    st.markdown(
                        "<span style='font-size:12px;color:#8884aa'>Session type</span>",
                        unsafe_allow_html=True,
                    )
                    current_tags = ev.get("tags", [])
                    tag_cols = st.columns(3)
                    for ci, tag in enumerate(CLASS_TAGS):
                        with tag_cols[ci]:
                            is_on = tag in current_tags
                            if st.button(
                                tag,
                                key=f"tag_{eid}_{ci}",
                                type="primary" if is_on else "secondary",
                            ):
                                tags = list(current_tags)
                                if tag in tags:
                                    tags.remove(tag)
                                else:
                                    tags.append(tag)
                                ev["tags"] = tags
                                st.rerun()

                # ── Office timing / cancelled ─────────────────────────────
                office_cancelled = False
                if etype == "office":
                    ev["officeCancelled"] = st.checkbox(
                        "Cancelled?", value=ev.get("officeCancelled", False),
                        key=f"cancelled_{eid}",
                    )
                    office_cancelled = ev["officeCancelled"]
                    if office_cancelled:
                        ev["note"] = st.text_input(
                            "Reason (optional)",
                            placeholder="e.g. Instructor unavailable",
                            key=f"note_{eid}",
                        )
                    else:
                        st.markdown("<span style='font-size:12px;color:#8884aa'>Timing</span>",
                                    unsafe_allow_html=True)
                        tb1, tb2 = st.columns(2)
                        with tb1:
                            if st.button(
                                "⬆ Before class", key=f"before_{eid}",
                                type="primary" if ev["officeTiming"] == "before" else "secondary",
                            ):
                                ev["officeTiming"] = "before"
                                st.rerun()
                        with tb2:
                            if st.button(
                                "⬇ After class", key=f"after_{eid}",
                                type="primary" if ev["officeTiming"] == "after" else "secondary",
                            ):
                                ev["officeTiming"] = "after"
                                st.rerun()

                # ── Extra credit ─────────────────────────────────────────
                if etype == "due":
                    ev["extraCredit"] = st.checkbox(
                        "Extra credit?", value=ev["extraCredit"],
                        key=f"ec_{eid}",
                    )

                # ── Ungraded ─────────────────────────────────────────────
                if etype == "optional":
                    ev["ungraded"] = st.checkbox(
                        "Ungraded?", value=ev["ungraded"],
                        key=f"ug_{eid}",
                    )

                # ── No Class reason + note ────────────────────────────────
                if etype == "noclass":
                    ev["noClassType"] = st.selectbox(
                        "Reason", NOCLASS_TYPES,
                        index=NOCLASS_TYPES.index(
                            ev.get("noClassType", NOCLASS_TYPES[0])),
                        key=f"noclasstype_{eid}",
                    )
                    ev["note"] = st.text_input(
                        "Note (optional)",
                        placeholder="e.g. Class rescheduled to Jun 10…",
                        key=f"note_{eid}",
                    )

                # ── Times (not for No Class or cancelled Office Hours) ────
                if etype != "noclass" and not office_cancelled:
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        ev["timePT"] = st.text_input(
                            "Time (PT)", placeholder="e.g. 5:00 PM",
                            key=f"pt_{eid}",
                        )
                    with tc2:
                        ev["timeET"] = st.text_input(
                            "Time (ET)", placeholder="e.g. 8:00 PM",
                            key=f"et_{eid}",
                        )
                    with tc3:
                        ev["timeUK"] = st.text_input(
                            "Time (UK)", placeholder="e.g. 1:00 AM",
                            key=f"uk_{eid}",
                        )

            # ── Apply pending action ──────────────────────────────────────
            if action:
                op, idx = action
                lst = st.session_state.events[day]
                if op == "delete":
                    lst.pop(idx)
                elif op == "up" and idx > 0:
                    lst[idx - 1], lst[idx] = lst[idx], lst[idx - 1]
                elif op == "down" and idx < len(lst) - 1:
                    lst[idx], lst[idx + 1] = lst[idx + 1], lst[idx]
                st.rerun()

            # ── Add event ─────────────────────────────────────────────────
            if st.button(f"+ Add event", key=f"add_{day}"):
                ev = _blank_event("class")
                _init_event_widgets(ev)
                st.session_state.events[day].append(ev)
                st.rerun()


# ============================================================
# RIGHT — Preview + Download
# ============================================================
with right:
    st.markdown("### Preview")
    st.caption("480 px · Discord ready")

    def _build_data() -> dict:
        ws = st.session_state.week_start
        we = ws + timedelta(days=4) if ws else None
        # Pull all field values from session-state widget keys so they're current
        days_data = {}
        for d in DAYS:
            evs = []
            for ev in st.session_state.events[d]:
                eid = ev["id"]
                evs.append({
                    **ev,
                    "title":    st.session_state.get(f"title_{eid}", ev["title"]),
                    "classNum": st.session_state.get(f"cls_{eid}",   ev["classNum"]),
                    "note":     st.session_state.get(f"note_{eid}",  ev["note"]),
                    "timePT":   st.session_state.get(f"pt_{eid}",    ev["timePT"]),
                    "timeET":   st.session_state.get(f"et_{eid}",    ev["timeET"]),
                    "timeUK":   st.session_state.get(f"uk_{eid}",    ev.get("timeUK", "")),
                    "tags":     ev.get("tags", []),
                })
            days_data[d] = evs
        return {
            "name":        st.session_state.course,
            "instructor":  st.session_state.instructor,
            "channel":     st.session_state.channel,
            "footerLine":  st.session_state.footer_line,
            "weekStart":   ws.isoformat() if ws else "",
            "weekEnd":     we.isoformat() if we else "",
            "days":        days_data,
        }

    graphic_data = _build_data()

    scheme = st.session_state.scheme

    # ── Preview at 1× (renders at exactly 480 px; displayed at 480 px) ──
    try:
        preview_img = render_graphic(graphic_data, scale=1, scheme=scheme)
        st.markdown(_preview_html(preview_img), unsafe_allow_html=True)
    except Exception as exc:
        st.error(f"Preview error: {exc}")

    st.markdown("---")

    # ── Download at 3× ──────────────────────────────────────────────────
    try:
        hi_res = render_graphic(graphic_data, scale=3, scheme=scheme)
        buf = io.BytesIO()
        hi_res.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        slug     = re.sub(r"[^\w\-]", "-",
                         (graphic_data["name"] or "schedule").lower().replace(" ", "-"))
        slug     = re.sub(r"-{2,}", "-", slug).strip("-") or "schedule"
        week     = graphic_data["weekStart"] or "week"
        filename = f"elvtr-{slug}-{week}.png"

        st.download_button(
            label="⬇ Download PNG",
            data=buf,
            file_name=filename,
            mime="image/png",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"Download error: {exc}")
