# pages/4_📅_Schedule.py
import streamlit as st
import pandas as pd

#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local
from utils.ui import apply_theme

st.set_page_config(page_title="Schedule", page_icon="📅", layout="wide")
apply_theme()


def _load_schedule() -> pd.DataFrame:
    fixtures = db.list_fixtures()
    if not fixtures:
        return pd.DataFrame()

    df = pd.DataFrame(fixtures)
    # Normalize columns for display
    column_map = {
        "match_id": "Match",
        "match_date": "Date",
        "date": "Date",
        "team_a": "Home",
        "team_b": "Away",
        "week": "Week",
        "day": "Day",
        "time_ist": "Time (IST)",
        "venue": "Venue",
    }
    df = df.rename(columns=column_map)
    if "Time (IST)" in df.columns:
        df["Time (IST)"] = df["Time (IST)"].astype(str).str.strip()
    if "Venue" in df.columns:
        df["Venue"] = df["Venue"].astype(str).str.strip()
    order_cols = [
        c
        for c in ["Week", "Match", "Date", "Day", "Time (IST)", "Home", "Away", "Venue"]
        if c in df.columns
    ]
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        sort_cols = [c for c in ["Week", "Date", "Match"] if c in df.columns]
        df = df.sort_values(sort_cols, na_position="last")
        df["Date"] = df["Date"].dt.strftime("%d %b %Y")
    else:
        sort_cols = [c for c in ["Week", "Match"] if c in df.columns]
        df = df.sort_values(sort_cols, na_position="last")
    if "Week" in df.columns:
        df["Week"] = df["Week"].fillna("TBD")
    return df[order_cols]


def main():
    st.title("📅 Season Schedule")
    st.caption("View-only schedule with venue and IST start time. Predictions must be submitted from the Make Predictions page.")

    df = _load_schedule()
    if df.empty:
        st.info("No fixtures uploaded yet. Please check back later.")
        return

    table = df.reset_index(drop=True)
    column_config = {
        "Week": st.column_config.Column("Week", width="small"),
        "Match": st.column_config.Column("Match", width="small"),
        "Date": st.column_config.Column("Date", width="medium"),
        "Day": st.column_config.Column("Day", width="small"),
        "Time (IST)": st.column_config.Column("Time (IST)", width="small"),
        "Home": st.column_config.Column("Home", width="medium"),
        "Away": st.column_config.Column("Away", width="medium"),
        "Venue": st.column_config.Column("Venue", width="large"),
    }
    visible_column_config = {k: v for k, v in column_config.items() if k in table.columns}
    dynamic_height = min(900, max(320, 60 + 32 * len(table)))
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config=visible_column_config,
        height=dynamic_height,
    )


if __name__ == "__main__":
    main()
