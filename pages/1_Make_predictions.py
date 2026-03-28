# pages/1_🏏_Make_Predictions.py
import json
from datetime import datetime, timezone, timedelta
from time import sleep
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 environments without tzdata
    ZoneInfo = None

import streamlit as st
from utils import db_pg as db      # Supabase
#from utils import db as db       # (optional) SQLite local

from utils.ui import apply_theme, match_card
from config import cutoff_dt_utc, POINTS

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
    st.caption(
        f"Scoring: {POINTS['match_winner']} pts/match winner • {POINTS['playoff_team']} per playoff team • "
        f"{POINTS['finalist']} per finalist • {POINTS['champion']} for champion"
    )

    if "email" not in st.session_state:
        st.warning("Please sign in on the Home page first.")
        st.stop()

    now_utc = datetime.now(timezone.utc)
    is_locked = locked(now_utc)
    if is_locked:
        st.info("Predictions are locked. Showing your submitted picks for reference.")

    @st.cache_data(show_spinner=False)
    def _cached_fixtures():
        return db.list_fixtures()

    fixtures = _cached_fixtures()
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
                champion_index = None
                if existing_champion and existing_champion in (teams or []):
                    champion_index = teams.index(existing_champion)
                champion = st.selectbox(
                    "Pick the champion",
                    options=teams,
                    index=champion_index,
                    placeholder="Please select",
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
        if not champion:
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

        # Save match picks in one DB transaction to reduce partial writes on slow connections
        pending_predictions = {}
        for f in fixtures:
            match_id = str(f["match_id"])
            if fixture_lock_state.get(match_id, False):
                continue
            key = f"pred_{f['match_id']}"
            sel = st.session_state.get(key)
            if sel in (f["team_a"], f["team_b"]):
                pending_predictions[match_id] = sel

        email = st.session_state["email"]
        remaining_predictions = dict(pending_predictions)
        missing_after_save = []

        # Save + verify, then retry once for any missing rows (handles transient slow DB/network)
        for attempt in range(2):
            db.save_match_predictions_bulk(email, remaining_predictions)
            saved_predictions = db.get_user_match_predictions(email)

            missing_after_save = [
                match_id
                for match_id, picked_winner in remaining_predictions.items()
                if saved_predictions.get(match_id) != picked_winner
            ]

            if not missing_after_save:
                break

            if attempt == 0:
                sleep(1)
                remaining_predictions = {
                    match_id: remaining_predictions[match_id] for match_id in missing_after_save
                }

        if missing_after_save:
            st.error(
                "Some matches could not be confirmed as saved even after an automatic retry. "
                "Please click Save again. Missing: "
                + ", ".join(missing_after_save)
            )
            st.stop()

        st.success("Saved! All available match predictions were stored.")

if __name__ == "__main__":
    main()