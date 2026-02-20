# pages/1_🏏_Make_Predictions.py
from datetime import datetime, timezone
import json
import streamlit as st
from utils import db_pg as db
from config import cutoff_dt_utc

st.set_page_config(page_title="Make Predictions", page_icon="🏏", layout="wide")

def locked():
    now_utc = datetime.now(timezone.utc)
    return now_utc >= cutoff_dt_utc()

def prediction_form(email: str):
    st.write("Make your selections and click **Save**. You can save multiple times before the cutoff.")

    # Load fixtures
    fixtures = db.list_fixtures()
    if not fixtures:
        st.warning("Fixtures are not yet uploaded. Please check back later.")
        return

    # Load existing picks
    match_picks = db.get_user_match_predictions(email)
    meta = db.get_meta_predictions(email)
    existing_playoffs, existing_finalists, existing_champion = [], [], None
    if meta:
        try:
            existing_playoffs = json.loads(meta["playoff_teams"] or "[]")
            existing_finalists = json.loads(meta["finalists"] or "[]")
            existing_champion = meta["champion"]
        except Exception:
            pass

    teams = db.list_teams()

    # Meta predictions
    st.subheader("Season Predictions")
    c1, c2 = st.columns([2, 1])
    with c1:
        playoffs = st.multiselect("Pick 4 playoff teams", options=teams, default=existing_playoffs, max_selections=4)
        finalists = st.multiselect("Pick 2 finalists", options=teams, default=existing_finalists, max_selections=2)
        champion = st.selectbox("Pick the champion", options=[""] + teams, index=([""] + teams).index(existing_champion) if existing_champion in (teams or []) else 0)
    with c2:
        st.info("You can pick finalists/champion independent of playoff picks (but typically they should be among your playoff picks).")

    st.divider()
    st.subheader("Match-by-Match Winners")

    # Long form list — grouped by week
    weeks = sorted({f["week"] for f in fixtures if f["week"] is not None})
    expanded = st.checkbox("Expand all weeks", value=False)

    for w in weeks:
        with st.expander(f"Week {w}", expanded=expanded):
            week_fixtures = [f for f in fixtures if f["week"] == w]
            for f in week_fixtures:
                mid = f["match_id"]
                label = f'{f["match_id"]}: {f["team_a"]} vs {f["team_b"]} — {f["match_date"]}'
                # default selection from previous save
                default = match_picks.get(mid, f["team_a"])
                st.radio(
                    label,
                    key=f"pred_{mid}",
                    options=[f["team_a"], f["team_b"]],
                    index=[f["team_a"], f["team_b"]].index(default) if default in [f["team_a"], f["team_b"]] else 0,
                    horizontal=True,
                )

    if st.button("💾 Save Predictions", type="primary", use_container_width=True):
        # Save meta
        if champion == "":
            st.error("Please select a champion.")
            return
        if len(playoffs) != 4:
            st.error("Please pick exactly 4 playoff teams.")
            return
        if len(finalists) != 2:
            st.error("Please pick exactly 2 finalists.")
            return

        db.save_meta_predictions(email, playoffs, finalists, champion)

        # Save match picks
        for f in fixtures:
            sel = st.session_state.get(f"pred_{f['match_id']}", f["team_a"])
            db.save_match_prediction(email, f["match_id"], sel)

        st.success("Saved! You can modify until the cutoff.")

def main():
    st.title("🏏 Make Predictions")

    if "email" not in st.session_state:
        st.warning("Please sign in on the Home page first.")
        st.stop()

    if locked():
        st.error("Predictions are locked. The cutoff has passed.")
        st.stop()

    prediction_form(st.session_state["email"])

if __name__ == "__main__":
    main()