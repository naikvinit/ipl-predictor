# pages/3_🗓️_Weekly_Winners.py
import streamlit as st
from utils.ui import apply_theme
from utils.scoring import weekly_winners
#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local
from config import POINTS

st.set_page_config(page_title="Weekly Winners", page_icon="🗓️", layout="wide")
apply_theme()

def main():
    st.title("🗓️ Weekly Winners")
    st.caption(
        f"Scoring: {POINTS['match_winner']} pts/match winner • {POINTS['playoff_team']} per playoff team • "
        f"{POINTS['finalist']} per finalist • {POINTS['champion']} for champion. "
        "Ties break on the longest streak of correct picks in that week."
    )

    weekly_totals, winners_by_week = weekly_winners()
    if weekly_totals.empty:
        st.warning("No weekly scores yet. Enter results to see weekly standings.")
        return

    weeks = db.list_weeks()
    if not weeks:
        st.warning("No weeks found in fixtures.")
        return

    collapse_all = st.checkbox("Collapse weekly tables", value=False)

    for w in weeks:
        with st.expander(f"Week {w}", expanded=not collapse_all):
            winners = winners_by_week.get(w)
            if winners is None or winners.empty:
                st.write("_No completed matches in this week yet._")
                continue

            names = ", ".join(winners["name"].tolist())
            score = int(winners["match_points"].max())
            streak = int(winners["best_streak"].max())

            st.markdown(
                f"""
                <div class="winner-card">
                  <div style="display:flex;align-items:center;gap:.5rem;">
                    <div style="font-size:2rem;">🏆</div>
                    <div>
                      <div><b>{names}</b></div>
                      <div class="muted">Score: {score} • Best streak: {streak}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Full table for that week (no emails)
            sub = weekly_totals[weekly_totals["week"] == w][["name", "match_points", "best_streak"]]
            st.dataframe(
                sub.rename(columns={"match_points": "Points", "best_streak": "Best streak"}),
                use_container_width=True,
                hide_index=True,
            )

if __name__ == "__main__":
    main()