# pages/4_🛠️_Admin.py
import io, csv, os
from pathlib import Path
import streamlit as st
import pandas as pd

#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local
from utils.ui import apply_theme
from utils.auth import refresh_authorized_users
from config import ADMIN_CODE

ROSTER_PATH = Path("data/authorized_users.csv")
ROSTER_COLUMNS = ["email", "name"]
ROSTER_COMMENT = "# List of allowed participants. Remove sample rows and add your league's emails."

st.set_page_config(page_title="Admin", page_icon="🛠️", layout="wide")
apply_theme()

def get_admin_code():
    # Prefer Streamlit secrets or env var
    code = None
    try:
        code = st.secrets.get("ADMIN_CODE")
    except Exception:
        pass
    return code or os.getenv("ADMIN_CODE") or ADMIN_CODE

def require_admin():
    if st.session_state.get("is_admin"):
        return True
    with st.form("admin_login"):
        code = st.text_input("Enter Admin Code", type="password")
        submitted = st.form_submit_button("Unlock Admin")
        if submitted:
            if code == get_admin_code():
                st.session_state["is_admin"] = True
                st.success("Admin unlocked.")
                return True
            else:
                st.error("Incorrect admin code.")
                return False
    return False

def parse_csv(file, expected_cols):
    # Handle BOM
    try:
        content = file.getvalue().decode("utf-8-sig")
    except Exception:
        content = file.getvalue().decode("latin-1")
    reader = csv.DictReader(io.StringIO(content))
    missing = [c for c in expected_cols if c not in (reader.fieldnames or [])]
    if missing:
        st.error(f"CSV missing columns: {missing}. Found columns: {reader.fieldnames}")
        return None
    return [row for row in reader]


def _clean_roster_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=ROSTER_COLUMNS)

    work = df.copy()
    missing = [c for c in ROSTER_COLUMNS if c not in work.columns]
    if missing:
        raise ValueError(f"Roster CSV missing columns: {', '.join(missing)}")

    work["email"] = work["email"].fillna(" ").astype(str).str.strip().str.lower()
    work["name"] = work["name"].fillna(" ").astype(str).str.strip()
    work = work[work["email"] != ""]
    work = work.drop_duplicates(subset=["email"], keep="last").reset_index(drop=True)
    return work[ROSTER_COLUMNS]


def _load_roster_df() -> pd.DataFrame:
    if not ROSTER_PATH.exists():
        return pd.DataFrame(columns=ROSTER_COLUMNS)
    try:
        raw = pd.read_csv(ROSTER_PATH, comment="#")
        return _clean_roster_df(raw)
    except ValueError as exc:
        st.error(f"Cannot read roster: {exc}")
    except Exception as exc:
        st.error(f"Cannot open roster CSV: {exc}")
    return pd.DataFrame(columns=ROSTER_COLUMNS)


def _save_roster_df(df: pd.DataFrame) -> int:
    cleaned = _clean_roster_df(df)
    ROSTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ROSTER_PATH.open("w", encoding="utf-8", newline="") as handle:
        handle.write(ROSTER_COMMENT + "\n")
        writer = csv.DictWriter(handle, fieldnames=ROSTER_COLUMNS)
        writer.writeheader()
        writer.writerows(cleaned.to_dict("records"))
    refresh_authorized_users()
    return len(cleaned)

def fixtures_ui():
    with st.expander("📥 Upload Fixtures", expanded=False):
        st.caption("CSV must include: match_id (int), match_date (ISO), team_a, team_b, week (int)")
        f = st.file_uploader("fixtures.csv", type=["csv"], key="fixtures_upload")
        if f and st.button("Import Fixtures", type="primary"):
            rows = parse_csv(f, ["match_id", "match_date", "team_a", "team_b", "week"])
            if rows is not None:
                payload = []
                for r in rows:
                    payload.append({
                        "match_id": int(r["match_id"]),
                        "match_date": r["match_date"],
                        "team_a": r["team_a"],
                        "team_b": r["team_b"],
                        "week": int(r["week"]),
                    })
                db.insert_fixtures(payload)
                st.success(f"Imported {len(payload)} fixtures.")

    data = db.list_fixtures()
    if data:
        df = pd.DataFrame(data)
        # Defensive: coerce and order by match_id asc, then date
        if "match_id" in df.columns:
            df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce")
        df = df.sort_values(["match_id", "match_date"], ascending=[True, True], na_position="last")
        st.markdown("#### Current Fixtures")
        st.markdown('<div class="df-light">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

def results_ui():
    with st.expander("📤 Upload Results", expanded=False):
        st.caption("CSV must include: match_id (int), winner (team name exactly as fixtures)")
        f = st.file_uploader("results.csv", type=["csv"], key="results_upload")
        if f and st.button("Import Results", type="primary"):
            rows = parse_csv(f, ["match_id", "winner"])
            if rows is not None:
                payload = [{"match_id": int(r["match_id"]), "winner": r["winner"]} for r in rows]
                db.insert_results(payload)
                st.success(f"Imported {len(payload)} results.")

def actuals_ui():
    with st.expander("🏆 Set Actuals (Playoffs / Finalists / Champion)", expanded=False):
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
        champion = st.selectbox("Actual Champion", [""] + teams,
                                index=([""] + teams).index(actual_champion) if actual_champion in (teams or []) else 0)

        if st.button("Save Actuals", type="primary"):
            if len(playoffs) != 4 or len(finalists) != 2 or champion == "":
                st.error("Please provide exactly 4 playoff teams, 2 finalists, and a champion.")
            else:
                db.set_actual_meta("playoff_teams", playoffs)
                db.set_actual_meta("finalists", finalists)
                db.set_actual_meta("champion", champion)
                st.success("Saved actual playoff teams, finalists, and champion.")


def roster_ui():
    with st.expander("👥 Manage Authorized Players", expanded=False):
        st.caption("Control which emails can sign in. CSV must contain columns: email, name.")
        roster_df = _load_roster_df()
        st.write(f"Current authorized players: {len(roster_df)}")

        download_payload = ROSTER_COMMENT + "\n" + ",".join(ROSTER_COLUMNS) + "\n"
        if ROSTER_PATH.exists():
            try:
                download_payload = ROSTER_PATH.read_text(encoding="utf-8")
            except Exception:
                pass
        st.download_button(
            "Download roster CSV",
            data=download_payload,
            file_name="authorized_users.csv",
            mime="text/csv",
        )

        uploaded = st.file_uploader("Upload CSV to replace roster", type=["csv"], key="roster_upload")
        if uploaded is not None:
            try:
                uploaded_df = pd.read_csv(uploaded, comment="#")
                cleaned_upload = _clean_roster_df(uploaded_df)
                st.markdown("##### Uploaded preview")
                st.dataframe(cleaned_upload, use_container_width=True, hide_index=True)
                if st.button("Replace roster with uploaded file", key="replace_roster_btn"):
                    count = _save_roster_df(cleaned_upload)
                    st.success(f"Roster replaced with {count} authorized players.")
                    st.rerun()
            except ValueError as exc:
                st.error(f"Upload error: {exc}")
            except Exception as exc:
                st.error(f"Unable to process uploaded CSV: {exc}")

        st.markdown("#### Edit roster inline")
        edit_source = roster_df if not roster_df.empty else pd.DataFrame(columns=ROSTER_COLUMNS)
        edited_df = st.data_editor(
            edit_source,
            num_rows="dynamic",
            use_container_width=True,
            key="roster_editor",
            column_order=ROSTER_COLUMNS,
            column_config={
                "email": st.column_config.TextColumn("email", help="Required; stored in lowercase."),
                "name": st.column_config.TextColumn("name", help="Display name shown in the app."),
            },
        )
        if st.button("Save roster changes", type="primary", key="save_roster_btn"):
            try:
                count = _save_roster_df(edited_df)
                st.success(f"Saved {count} authorized players.")
                st.rerun()
            except ValueError as exc:
                st.error(f"Cannot save roster: {exc}")

def danger_zone_ui():
    with st.expander("🧨 Danger Zone", expanded=False):
        st.caption("Delete all data (use with caution).")
        confirm = st.text_input("Type 'RESET' to confirm")
        if st.button("⚠️ Reset Database", type="secondary"):
            if confirm != "RESET":
                st.error("Please type 'RESET' exactly to confirm.")
            else:
                try:
                    # Hard wipes (order matters due to FKs)
                    from sqlalchemy import text
                    engine = db.get_engine()
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM predictions_match;"))
                        conn.execute(text("DELETE FROM predictions_meta;"))
                        conn.execute(text("DELETE FROM results;"))
                        conn.execute(text("DELETE FROM fixtures;"))
                        conn.execute(text("DELETE FROM users;"))
                        conn.execute(text("DELETE FROM meta_actuals;"))
                    st.success("Database wiped. Reload the page.")
                except Exception as e:
                    st.error(f"Reset failed: {e}")

def main():
    st.title("🛠️ Admin")
    if not require_admin():
        st.stop()

    fixtures_ui()
    results_ui()
    actuals_ui()
    roster_ui()
    danger_zone_ui()

if __name__ == "__main__":
    main()