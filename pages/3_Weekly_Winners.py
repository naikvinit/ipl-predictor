# pages/3_🗓️_Weekly_Winners.py
import streamlit as st
from utils.scoring import weekly_winners
from utils import db_pg as db

st.set_page_config(page_title="Weekly Winners", page_icon="🗓️", layout="wide")

def main():
    st.title("🗓️ Weekly Winners")

    weekly_totals, winners_by_week = weekly_winners()

    if weekly_totals.empty:
        st.info("No weekly scores yet. Enter results to see weekly standings.")
        return

    weeks = db.list_weeks()
    if not weeks:
        st.info("No weeks found in fixtures.")
        return

    for w in weeks:
        st.subheader(f"Week {w}")
        winners = winners_by_week.get(w)
        if winners is None or winners.empty:
            st.write("_No completed matches in this week yet._")
            continue

        # Winners (could be multiple ties)
        st.markdown("**Winner(s):**")
        st.dataframe(winners[["name", "email", "match_points"]], use_container_width=True, hide_index=True)

        # Full table for that week
        st.markdown("**All Scores:**")
        sub = weekly_totals[weekly_totals["week"] == w][["name", "email", "match_points"]]
        st.dataframe(sub, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()