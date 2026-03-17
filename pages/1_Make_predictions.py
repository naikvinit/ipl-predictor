# pages/1_🏏_Make_Predictions.py
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 environments without tzdata
    ZoneInfo = None

import streamlit as st
#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local

from utils.ui import apply_theme, match_card
from config import cutoff_dt_utc

st.set_page_config(page_title="Make Predictions", page_icon="🏏", layout="wide")
apply_theme()

IST_ZONE = None
if ZoneInfo is not None:
    try:
        IST_ZONE = ZoneInfo("Asia/Kolkata")
    except Exception:
        IST_ZONE = None
if IST_ZONE is None:
    IST_ZONE = timezone(timedelta(hours=5, minutes=30))


def locked(now_utc: Optional[datetime] = None) -> bool:
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    return now_utc >= cutoff_dt_utc(db_client=db)


def _parse_time_component(value: Optional[str]):
    if not value:
        return None
    sanitized = str(value).strip().upper().replace("IST", "").strip()
    if sanitized.endswith("AM") or sanitized.endswith("PM"):
        suffix = sanitized[-2:]
        prefix = sanitized[:-2].strip()
        sanitized = f"{prefix} {suffix}"
    time_formats = ("%H:%M", "%I:%M %p", "%I %p")
    for fmt in time_formats:
        try:
            return datetime.strptime(sanitized, fmt).time()
        except ValueError:
            continue
    return None


def _parse_date_component(value: str):
    sanitized = str(value).strip()
    date_formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d %b %Y",
        "%d %b %y",
    )
    for fmt in date_formats:
        try:
            return datetime.strptime(sanitized, fmt).date()
        except ValueError:
            continue
    return None


def _fixture_datetime_utc(fixture: dict) -> Optional[datetime]:
    raw_date = fixture.get("match_date")
    if not raw_date:
        return None
    as_str = str(raw_date).strip()
    try:
        dt = datetime.fromisoformat(as_str)
        if dt.tzinfo is None:
            time_component = _parse_time_component(fixture.get("time_ist"))
            if time_component is not None:
                dt = dt.replace(
                    hour=time_component.hour,
                    minute=time_component.minute,
                    second=time_component.second,
                    microsecond=0,
                )
            dt = dt.replace(tzinfo=IST_ZONE)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    parsed_date = _parse_date_component(as_str)
    if not parsed_date:
        return None
    time_component = _parse_time_component(fixture.get("time_ist")) or datetime.min.time()
    dt = datetime.combine(parsed_date, time_component).replace(tzinfo=IST_ZONE)
    return dt.astimezone(timezone.utc)


def _fixture_has_started(fixture: dict, now_utc: datetime) -> bool:
    match_dt = _fixture_datetime_utc(fixture)
    if match_dt is None:
        return False
    return now_utc >= match_dt

def main():
    st.title("🏏 Make Predictions")

    if "email" not in st.session_state:
        st.warning("Please sign in on the Home page first.")
        st.stop()

    now_utc = datetime.now(timezone.utc)
    is_locked = locked(now_utc)
    if is_locked:
        st.info("Predictions are locked. Showing your submitted picks for reference.")

    fixtures = db.list_fixtures()
    if not fixtures:
        st.warning("Fixtures are not yet uploaded. Please check back later.")
        st.stop()

    # Load existing picks
    match_picks = db.get_user_match_predictions(st.session_state["email"])
    meta = db.get_meta_predictions(st.session_state["email"])
    existing_playoffs, existing_finalists, existing_champion = [], [], None
    if meta:
        try:
            existing_playoffs = json.loads(meta.get("playoff_teams") or "[]")
            existing_finalists = json.loads(meta.get("finalists") or "[]")
            existing_champion = meta.get("champion")
        except Exception:
            pass

    # Teams list for meta
    teams = db.list_teams()

    # Compute per-match lock state (global cutoff OR match already started)
    fixture_lock_state = {}
    any_started = False
    for f in fixtures:
        match_id = str(f.get("match_id"))
        started = _fixture_has_started(f, now_utc)
        if started:
            any_started = True
        fixture_lock_state[match_id] = is_locked or started

    if not is_locked and any_started:
        st.info("Matches that have already started are read-only even if the overall deadline moves.")

    # Meta predictions section
    with st.container():
        st.markdown("### 🧠 Season Predictions")
        c1, c2, c3 = st.columns([1.2, 1.2, 1])
        with c1:
            playoffs = st.multiselect(
                "Pick 4 playoff teams",
                options=teams,
                default=existing_playoffs,
                max_selections=4,
                disabled=is_locked,
            )
        with c2:
            finalists = st.multiselect(
                "Pick 2 finalists",
                options=teams,
                default=existing_finalists,
                max_selections=2,
                disabled=is_locked,
            )
        with c3:
            champion = st.selectbox(
                "Pick the champion",
                options=[""] + teams,
                index=([""] + teams).index(existing_champion) if existing_champion in (teams or []) else 0,
                disabled=is_locked,
            )

    st.divider()
    st.markdown("### 🗓️ Match-by-Match Winners")

    # Group by week (assumes integer week)
    weeks = sorted({f["week"] for f in fixtures if f.get("week") is not None})
    expand_all = st.checkbox("Expand all weeks", value=False)

    for w in weeks:
        with st.expander(f"Week {w}", expanded=expand_all):
            week_fixtures = [f for f in fixtures if f.get("week") == w]
            # Order by match_id if present, otherwise by date
            week_fixtures = sorted(week_fixtures, key=lambda x: (x.get("match_id", 0), str(x.get("match_date", ""))))
            for f in week_fixtures:
                pick = match_card(
                    fixture=f,
                    existing_pick=match_picks.get(str(f["match_id"]), None),
                    disabled=fixture_lock_state.get(str(f["match_id"]), is_locked),
                )

    if is_locked:
        st.warning("Edits are disabled because the cutoff has passed.")
        return

    if st.button("💾 Save Predictions", type="primary", use_container_width=True):
        if champion == "":
            st.error("Please select a champion.")
            st.stop()
        if len(playoffs) != 4:
            st.error("Please pick exactly 4 playoff teams.")
            st.stop()
        if len(finalists) != 2:
            st.error("Please pick exactly 2 finalists.")
            st.stop()

        # Save meta
        db.save_meta_predictions(st.session_state["email"], playoffs, finalists, champion)

        # Ensure every match has a pick before saving
        missing_matches = [
            f["match_id"]
            for f in fixtures
            if not fixture_lock_state.get(str(f["match_id"]), False)
            and st.session_state.get(f"pred_{f['match_id']}") not in (f["team_a"], f["team_b"])
        ]

        if missing_matches:
            st.error(
                "Please select a winner for every match before saving. Missing: "
                + ", ".join(str(m) for m in missing_matches)
            )
            st.stop()

        # Save match picks
        for f in fixtures:
            match_id = str(f["match_id"])
            if fixture_lock_state.get(match_id, False):
                continue
            key = f"pred_{f['match_id']}"
            sel = st.session_state.get(key)
            if sel in (f["team_a"], f["team_b"]):
                db.save_match_prediction(st.session_state["email"], f["match_id"], sel)

        st.success("Saved! You can modify until the cutoff.")

if __name__ == "__main__":
    main()