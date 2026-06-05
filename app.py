"""
ELVTR Weekly Schedule Generator — Streamlit app
"""
import io
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
section[data-testid="stMain"] > div { padding-top: 1rem; }
h1, h2, h3, label, .stText { color: #e8e6f8 !important; }
.stSelectbox > div, .stTextInput > div { background: #211f33; }
div[data-baseweb="select"] { background: #211f33 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
EVENT_TYPES = ["class", "office", "due", "optional", "holiday"]
TYPE_LABELS = {
    "class": "Class",
    "office": "Office Hours",
    "due": "Assignment Due",
    "optional": "Optional",
    "holiday": "Holiday",
}

def _blank_event(etype="class") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": etype,
        "title": "",
        "classNum": "",
        "officeTiming": "before",
        "extraCredit": False,
        "ungraded": False,
        "note": "",
        "timePT": "",
        "timeET": "",
    }

if "events" not in st.session_state:
    st.session_state.events = {d: [] for d in DAYS}
if "course" not in st.session_state:
    st.session_state.course = ""
if "instructor" not in st.session_state:
    st.session_state.instructor = ""
if "channel" not in st.session_state:
    st.session_state.channel = "#help"
if "week_start" not in st.session_state:
    st.session_state.week_start = None
if "week_end" not in st.session_state:
    st.session_state.week_end = None

# ---------------------------------------------------------------------------
# Layout: two columns
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

    st.markdown("---")
    st.markdown("### Week")

    col_s, col_e = st.columns(2)
    with col_s:
        raw_start = st.date_input(
            "Start date", value=st.session_state.week_start,
            key="inp_week_start",
        )
    with col_e:
        raw_end = st.date_input(
            "End date", value=st.session_state.week_end,
            key="inp_week_end",
        )

    # Auto-set Monday→Friday when start date changes
    if raw_start and raw_start != st.session_state.week_start:
        # snap to Monday of that week
        dow = raw_start.weekday()  # Mon=0
        mon = raw_start - timedelta(days=dow)
        fri = mon + timedelta(days=4)
        st.session_state.week_start = mon
        st.session_state.week_end = fri
        st.rerun()
    elif raw_start:
        st.session_state.week_start = raw_start
    if raw_end and raw_end != st.session_state.week_end:
        st.session_state.week_end = raw_end

    st.markdown("---")
    st.markdown("### Schedule")

    # ---- Day blocks ----
    for day in DAYS:
        with st.expander(day, expanded=True):
            events = st.session_state.events[day]
            to_delete = []

            for ev in events:
                eid = ev["id"]
                st.markdown(f"<hr style='border-color:#2e2b4a;margin:6px 0'>", unsafe_allow_html=True)

                col_type, col_del = st.columns([5, 1])
                with col_type:
                    new_type = st.selectbox(
                        "Type", EVENT_TYPES,
                        index=EVENT_TYPES.index(ev["type"]),
                        format_func=lambda t: TYPE_LABELS[t],
                        key=f"type_{eid}",
                    )
                with col_del:
                    st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_{eid}", help="Remove event"):
                        to_delete.append(eid)
                    st.markdown("</div>", unsafe_allow_html=True)

                if new_type != ev["type"]:
                    ev["type"] = new_type
                    # auto-fill office title
                    if new_type == "office" and not ev["title"]:
                        first = (st.session_state.instructor or "Instructor").split()[0]
                        ev["title"] = f"Open Q&A with {first}"

                # Title field
                default_title = ev["title"]
                ev["title"] = st.text_input(
                    "Title", value=default_title,
                    placeholder="Session title…",
                    key=f"title_{eid}",
                )

                # Type-specific extras
                etype = ev["type"]

                if etype == "class":
                    ev["classNum"] = st.text_input(
                        "Class #", value=ev["classNum"],
                        placeholder="e.g. 5",
                        key=f"cls_{eid}",
                    )

                if etype == "office":
                    st.markdown("<span style='font-size:12px;color:#8884aa'>Timing</span>",
                                unsafe_allow_html=True)
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        if st.button(
                            "⬆ Before class",
                            key=f"before_{eid}",
                            type="primary" if ev["officeTiming"] == "before" else "secondary",
                        ):
                            ev["officeTiming"] = "before"
                            st.rerun()
                    with tc2:
                        if st.button(
                            "⬇ After class",
                            key=f"after_{eid}",
                            type="primary" if ev["officeTiming"] == "after" else "secondary",
                        ):
                            ev["officeTiming"] = "after"
                            st.rerun()

                if etype == "due":
                    ev["extraCredit"] = st.checkbox(
                        "Extra credit?", value=ev["extraCredit"],
                        key=f"ec_{eid}",
                    )

                if etype == "optional":
                    ev["ungraded"] = st.checkbox(
                        "Ungraded?", value=ev["ungraded"],
                        key=f"ug_{eid}",
                    )

                if etype == "holiday":
                    ev["note"] = st.text_input(
                        "Note (optional)", value=ev["note"],
                        placeholder="e.g. Class rescheduled to Jun 10…",
                        key=f"note_{eid}",
                    )

                # Time fields (not shown for holiday)
                if etype != "holiday":
                    tc1, tc2 = st.columns(2)
                    with tc1:
                        ev["timePT"] = st.text_input(
                            "Time (PT)", value=ev["timePT"],
                            placeholder="e.g. 5:00 PM",
                            key=f"pt_{eid}",
                        )
                    with tc2:
                        ev["timeET"] = st.text_input(
                            "Time (ET)", value=ev["timeET"],
                            placeholder="e.g. 8:00 PM",
                            key=f"et_{eid}",
                        )

            # Remove deleted events
            if to_delete:
                st.session_state.events[day] = [
                    e for e in events if e["id"] not in to_delete
                ]
                st.rerun()

            # Add event button
            if st.button(f"+ Add event", key=f"add_{day}"):
                st.session_state.events[day].append(_blank_event("class"))
                st.rerun()


# ============================================================
# RIGHT — Preview + Download
# ============================================================
with right:
    st.markdown("### Preview")
    st.caption("480 px · Discord ready")

    def _build_data() -> dict:
        ws = st.session_state.week_start
        we = st.session_state.week_end
        return {
            "name": st.session_state.course,
            "instructor": st.session_state.instructor,
            "channel": st.session_state.channel,
            "weekStart": ws.isoformat() if ws else "",
            "weekEnd": we.isoformat() if we else "",
            "days": {d: list(st.session_state.events[d]) for d in DAYS},
        }

    graphic_data = _build_data()

    # Render preview (2x = 960px, displayed at 480px by Streamlit)
    try:
        preview_img = render_graphic(graphic_data, scale=2)
        st.image(preview_img, width=480)
    except Exception as exc:
        st.error(f"Preview error: {exc}")
        preview_img = None

    st.markdown("---")

    # Download button (3x = 1440px)
    try:
        hi_res = render_graphic(graphic_data, scale=3)
        buf = io.BytesIO()
        hi_res.save(buf, format="PNG", optimize=True)
        buf.seek(0)

        slug = (graphic_data["name"] or "schedule").lower().replace(" ", "-")
        week = graphic_data["weekStart"] or "week"
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
