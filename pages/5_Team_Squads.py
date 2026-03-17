# pages/5_👥_Team_Squads.py
import streamlit as st
import pandas as pd
from pathlib import Path

from utils.ui import apply_theme, _logo_or_fallback

DATA_PATH = Path("data/ipl_2026_all_teams_squads.csv")
ROLE_ORDER = ["Batter", "WK-Batter", "All-Rounder", "Bowler"]
CHECKBOX_PREFIX = "squad_team_"

st.set_page_config(page_title="Team Squads", page_icon="👥", layout="wide")
apply_theme()

@st.cache_data(show_spinner=False)
def load_squads(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    expected = {"Team", "Player", "Role"}
    if not expected.issubset(df.columns):
        missing = ", ".join(sorted(expected - set(df.columns)))
        st.error(f"Squad CSV missing columns: {missing}.")
        return pd.DataFrame()
    df = df[["Team", "Player", "Role"]].dropna(subset=["Team", "Player", "Role"]).copy()
    df["Team"] = df["Team"].astype(str).str.strip()
    df["Player"] = df["Player"].astype(str).str.strip()
    df["Role"] = df["Role"].astype(str).str.strip()
    return df

def render_team(team: str, team_df: pd.DataFrame) -> None:
    role_groups = (
        team_df.groupby("Role")["Player"]
        .apply(lambda players: sorted({p for p in players if p}))
        .to_dict()
    )
    if not role_groups:
        st.write("No players found for this team.")
        return

    ordered_roles = [role for role in ROLE_ORDER if role in role_groups]
    extras = sorted(set(role_groups) - set(ROLE_ORDER))
    ordered_roles.extend(extras)

    cols = st.columns(len(ordered_roles)) if ordered_roles else []
    for col, role in zip(cols, ordered_roles):
        with col:
            st.markdown(f"**{role}**")
            players = role_groups[role]
            if not players:
                st.caption("No players listed.")
                continue
            for player in players:
                st.markdown(f"- {player}")

def main() -> None:
    st.title("👥 Team Squads")
    st.caption("Browse every franchise roster grouped by playing role. Available without signing in.")

    squads = load_squads(DATA_PATH)
    if squads.empty:
        st.info("Squad data not available. Upload or verify data/ipl_2026_all_teams_squads.csv.")
        return

    teams = sorted(squads["Team"].unique())
    if not teams:
        st.info("No teams found in squad data.")
        return

    st.markdown("**Filter teams** — tap a name to toggle its squad. Use the quick actions for convenience.")
    controls = st.columns([1, 1, 6])
    with controls[0]:
        if st.button("Select all"):
            for team in teams:
                st.session_state[f"{CHECKBOX_PREFIX}{team}"] = True
            st.rerun()
    with controls[1]:
        if st.button("Clear all"):
            for team in teams:
                st.session_state[f"{CHECKBOX_PREFIX}{team}"] = False
            st.rerun()

    grid_cols = 4
    checkbox_state = {}
    cols = st.columns(grid_cols)
    for idx, team in enumerate(teams):
        key = f"{CHECKBOX_PREFIX}{team}"
        if key not in st.session_state:
            st.session_state[key] = True
        col = cols[idx % grid_cols]
        with col:
            checkbox_state[team] = st.checkbox(team, key=key)

    selected = [team for team, checked in checkbox_state.items() if checked]
    if not selected:
        st.warning("Select at least one team to view its squad.")
        return

    for idx, team in enumerate(selected):
        header_cols = st.columns([0.12, 0.88])
        logo = _logo_or_fallback(team)
        with header_cols[0]:
            if logo:
                st.image(logo, width=60)
        with header_cols[1]:
            st.markdown(
                f"""
                <div style="padding:0.25rem 0.75rem; border-left:4px solid #FF6B35; font-size:1.6rem; font-weight:600; margin:0;">
                    {team}
                </div>
                """,
                unsafe_allow_html=True,
            )
        render_team(team, squads[squads["Team"] == team])
        if idx < len(selected) - 1:
            st.divider()

if __name__ == "__main__":
    main()
