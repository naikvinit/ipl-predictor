# pages/2_📊_Leaderboard.py
import streamlit as st
from utils.scoring import overall_leaderboard

st.set_page_config(page_title="Leaderboard", page_icon="📊", layout="wide")

def main():
    st.title("📊 Overall Leaderboard")

    lb = overall_leaderboard()
    if lb.empty:
        st.info("No scores yet. Once results are entered, scores will appear here.")
        return

    st.dataframe(
        lb,
        use_container_width=True,
        hide_index=True,
    )

    csv = lb.to_csv(index=False).encode("utf-8")
    st.download_button("Download Leaderboard (CSV)", csv, "leaderboard.csv", "text/csv")

if __name__ == "__main__":
    main()