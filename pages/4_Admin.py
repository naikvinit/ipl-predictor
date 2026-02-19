# pages/4_🛠️_Admin.py
import io
import csv
import json
import os
import streamlit as st
from utils import db
from config import ADMIN_CODE

st.set_page_config(page_title="Admin", page_icon="🛠️", layout="wide")

def require_admin():
    if st.session_state.get("is_admin"):
        return True
    with st.form("admin_login"):
        code = st.text_input("Enter Admin Code", type="password")
        submitted = st.form_submit_button("Unlock Admin")
        if submitted:
            # Prefer Streamlit Secrets or env var over config fallback
            env_code = os.getenv("ADMIN_CODE") or ADMIN_CODE
            if not env_code:
                st.error("Admin code not configured. Set ENV var ADMIN_CODE or config.ADMIN_CODE.")
                return False
            if code == env_code:
                st.session_state["is_admin"] = True
                st.success("Admin unlocked.")
                return True
            else:
                st.error("Incorrect admin code.")
                return False
    return False

def parse_csv(file, expected_cols):
    try:
        content = file.getvalue().decode("utf-8-sig")
    except Exception:
        content = file.getvalue().decode("latin-1")
    reader = csv.DictReader(io.StringIO(content))
    missing = [c for c in expected_cols if c not in reader.fieldnames]
    if missing:
        st.error(f"CSV missing columns: {missing}. Found columns: {reader.fieldnames}")
        return None
    rows = [row for row in reader]
    return rows

def fixtures_ui():
    st.subheader("Upload Fixtures")
    st.caption("CSV columns required: match_id, match_date (ISO), team_a, team_b, week (int)")
    f = st.file_uploader("fixtures.csv", type=["csv"], key="fixtures_upload")
    if f and st.button("Import Fixtures", type="primary"):
        rows = parse_csv(f, ["match_id", "match_date", "team_a", "team_b", "week"])
        if rows is not None:
            # Clean types
            payload = []
            for r in rows:
                payload.append({
                    "match_id": str(r["match_id"]),
                    "match_date": r["match_date"],
                    "team_a": r["team_a"],
                    "team_b": r["team_b"],
                    "week": int(r["week"]),
                })
            db.insert_fixtures(payload)
            st.success(f"Imported {len(payload)} fixtures.")

    # Preview
    data = db.list_fixtures()
    if data:
        st.markdown("**Current Fixtures:**")
        import pandas as pd
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

def results_ui():
    st.subheader("Upload Results")
    st.caption("CSV columns required: match_id, winner (team name exactly as fixtures)")
    f = st.file_uploader("results.csv", type=["csv"], key="results_upload")
    if f and st.button("Import Results", type="primary"):
        rows = parse_csv(f, ["match_id", "winner"])
        if rows is not None:
            payload = [{"match_id": str(r["match_id"]), "winner": r["winner"]} for r in rows]
            db.insert_results(payload)
            st.success(f"Imported {len(payload)} results.")

def actuals_ui():
    st.subheader("Set Final Outcomes (for bonus points)")
    teams = db.list_teams()
    if not teams:
        st.info("Upload fixtures first to populate team list.")
        return

    # Existing saved values
    actual_playoffs = set(db.get_actual_meta("playoff_teams") or [])
    actual_finalists = set(db.get_actual_meta("finalists") or [])
    actual_champion = db.get_actual_meta("champion") or ""

    playoffs = st.multiselect("Actual 4 Playoff Teams", teams, default=list(actual_playoffs), max_selections=4)
    finalists = st.multiselect("Actual 2 Finalists", teams, default=list(actual_finalists), max_selections=2)
    champion = st.selectbox("Actual Champion", [""] + teams, index=([""] + teams).index(actual_champion) if actual_champion in (teams or []) else 0)

    if st.button("Save Actuals", type="primary"):
        if len(playoffs) != 4 or len(finalists) != 2 or champion == "":
            st.error("Please provide exactly 4 playoff teams, 2 finalists, and a champion.")
        else:
            db.set_actual_meta("playoff_teams", playoffs)
            db.set_actual_meta("finalists", finalists)
            db.set_actual_meta("champion", champion)
            st.success("Saved actual playoff teams, finalists, and champion.")

def main():
    st.title("🛠️ Admin")

    if not require_admin():
        st.stop()

    tabs = st.tabs(["Fixtures", "Results", "Final Outcomes"])
    with tabs[0]:
        fixtures_ui()
    with tabs[1]:
        results_ui()
    with tabs[2]:
        actuals_ui()

if __name__ == "__main__":
    main()