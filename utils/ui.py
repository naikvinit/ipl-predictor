# utils/ui.py
from __future__ import annotations
import os
from typing import Dict, Optional
import streamlit as st

# Map full team names to logo paths (put PNGs in assets/logos)
TEAM_LOGOS: Dict[str, str] = {
    "Chennai Super Kings": "assets/logos/csk.png",
    "Mumbai Indians": "assets/logos/mi.png",
    "Royal Challengers Bangalore": "assets/logos/rcb.png",
    "Royal Challengers Bengaluru": "assets/logos/rcb.png",  # new branding
    "Kolkata Knight Riders": "assets/logos/kkr.png",
    "Rajasthan Royals": "assets/logos/rr.png",
    "Sunrisers Hyderabad": "assets/logos/srh.png",
    "Lucknow Super Giants": "assets/logos/lsg.png",
    "Gujarat Titans": "assets/logos/gt.png",
    "Delhi Capitals": "assets/logos/dc.png",
    "Punjab Kings": "assets/logos/pbks.png",
}

def _logo_or_fallback(team: str) -> Optional[str]:
    path = TEAM_LOGOS.get(team)
    return path if path and os.path.exists(path) else None

def apply_theme():
    """Load global CSS once per page."""
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def format_match_dt(dt_str: str) -> str:
    # Keep it simple; your date strings are ISO-like. We’ll just show as-is.
    # You can parse and prettify if needed.
    return dt_str or ""

PLACEHOLDER_LABEL = "- Select winner -"


def match_card(fixture: dict, existing_pick: Optional[str], *, disabled: bool = False) -> Optional[str]:
    """Render a Cricbuzz-like match card and return the selected team."""
    t1, t2 = fixture["team_a"], fixture["team_b"]
    logo1, logo2 = _logo_or_fallback(t1), _logo_or_fallback(t2)
    options = [PLACEHOLDER_LABEL, t1, t2]
    pick_default = existing_pick if existing_pick in (t1, t2) else PLACEHOLDER_LABEL

    st.markdown('<div class="match-card">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 1, 1.2])
    with c1:
        if logo1: st.image(logo1, width=48)
        st.markdown(f"<div class='team-name'>{t1}</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='match-vs'>VS</div>", unsafe_allow_html=True)
        st.caption(f"Match #{fixture['match_id']}")
        st.caption(format_match_dt(fixture.get("match_date", "")))
        venue = (fixture.get("venue") or "").strip()
        if venue:
            st.caption(f"Ground: {venue}")

    with c3:
        if logo2: st.image(logo2, width=48)
        st.markdown(f"<div class='team-name'>{t2}</div>", unsafe_allow_html=True)

    # The radio (horizontal) for prediction
    choice = st.radio(
        label="",
        options=options,
        index=options.index(pick_default),
        horizontal=True,
        key=f"pred_{fixture['match_id']}",
        disabled=disabled,
    )

    st.markdown("</div>", unsafe_allow_html=True)
    return choice if choice in (t1, t2) else None