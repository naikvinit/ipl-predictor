# pages/1_🏏_Make_Predictions.py
import json
from datetime import datetime, timezone
import streamlit as st
#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local

from utils.ui import apply_theme, match_card
from config import cutoff_dt_utc

st.set_page_config(page_title="Make Predictions", page_icon="🏏", layout="wide")
apply_theme()

def locked():
    now_utc = datetime.now(timezone.utc)
    return now_utc >= cutoff_dt_utc()

def main():
    st.title("🏏 Make Predictions")

    if "email" not in st.session_state:
        st.warning("Please sign in on the Home page first.")
        st.stop()

    if locked():
        st.error("Predictions are locked. The cutoff has passed.")
        st.stop()

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

    # Meta predictions section
    with st.container():
        st.markdown("### 🧠 Season Predictions")
        c1, c2, c3 = st.columns([1.2, 1.2, 1])
        with c1:
            playoffs = st.multiselect("Pick 4 playoff teams", options=teams, default=existing_playoffs, max_selections=4)
        with c2:
            finalists = st.multiselect("Pick 2 finalists", options=teams, default=existing_finalists, max_selections=2)
        with c3:
            champion = st.selectbox("Pick the champion", options=[""] + teams,
                                    index=([""] + teams).index(existing_champion) if existing_champion in (teams or []) else 0)

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
                pick = match_card(fixture=f, existing_pick=match_picks.get(str(f["match_id"]), None))

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
            if st.session_state.get(f"pred_{f['match_id']}") not in (f["team_a"], f["team_b"])
        ]

        if missing_matches:
            st.error(
                "Please select a winner for every match before saving. Missing: "
                + ", ".join(str(m) for m in missing_matches)
            )
            st.stop()

        # Save match picks
        for f in fixtures:
            key = f"pred_{f['match_id']}"
            sel = st.session_state.get(key)
            db.save_match_prediction(st.session_state["email"], f["match_id"], sel)

        st.success("Saved! You can modify until the cutoff.")

if __name__ == "__main__":
    main()