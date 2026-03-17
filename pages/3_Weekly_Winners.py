# pages/3_🗓️_Weekly_Winners.py
import streamlit as st
from utils.ui import apply_theme
from utils.scoring import weekly_winners
#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local

st.set_page_config(page_title="Weekly Winners", page_icon="🗓️", layout="wide")
apply_theme()

def main():
    st.title("🗓️ Weekly Winners")

    weekly_totals, winners_by_week = weekly_winners()
    if weekly_totals.empty:
        st.warning("No weekly scores yet. Enter results to see weekly standings.")
        return

    weeks = db.list_weeks()
    if not weeks:
        st.warning("No weeks found in fixtures.")
        return

    for w in weeks:
        st.subheader(f"Week {w}")
        winners = winners_by_week.get(w)
        if winners is None or winners.empty:
            st.write("_No completed matches in this week yet._")
            continue

        names = ", ".join(winners["name"].tolist())
        score = int(winners["match_points"].max())

        st.markdown(
            f"""
            <div class="winner-card">
              <div style="display:flex;align-items:center;gap:.5rem;">
                <div style="font-size:2rem;">🏆</div>
                <div>
                  <div><b>{names}</b></div>
                  <div class="muted">Score: {score}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Full table for that week
        sub = weekly_totals[weekly_totals["week"] == w][["name", "email", "match_points"]]
        st.dataframe(sub.rename(columns={"match_points": "Points"}), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()