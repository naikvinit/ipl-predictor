# pages/2_📊_Leaderboard.py
import streamlit as st
from utils.ui import apply_theme
from utils.scoring import overall_leaderboard  # keep using your scoring module

st.set_page_config(page_title="Leaderboard", page_icon="📊", layout="wide")
apply_theme()

def render_leaderboard(df):
    df = df.copy()
    # Medal emojis
    df["medal"] = df["rank"].apply(lambda r: "🥇" if r == 1 else ("🥈" if r == 2 else ("🥉" if r == 3 else "")))
    df["Player"] = df["medal"] + " " + df["name"]

    st.markdown("### 📊 Season Leaderboard")
    st.dataframe(
        df[["rank", "Player", "match_points", "playoff_points", "finalist_points", "champion_points", "total_points"]],
        hide_index=True, use_container_width=True
    )

def main():
    lb = overall_leaderboard()
    if lb.empty:
        st.warning("No scores yet. Once results are entered, scores will appear here.")
        return
    render_leaderboard(lb)

if __name__ == "__main__":
    main()