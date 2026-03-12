# app.py
import streamlit as st
#from utils import db_pg as db      # Supabase
from utils import db as db       # (optional) SQLite local dev
from utils.ui import apply_theme
from utils.auth import load_authorized_users

from config import APP_TITLE

st.set_page_config(page_title=APP_TITLE, page_icon="🏏", layout="wide")
apply_theme()

def sign_in(authorized_users):
    if not authorized_users:
        st.info(
            "No authorized players found. Add entries to data/authorized_users.csv to enable sign-ins.")

    with st.form("signin"):
        name = st.text_input("Your Name")
        email = st.text_input("Email (used to track your predictions)").lower().strip()
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if not email or "@" not in email:
                st.error("Please enter a valid email address.")
                return
            existing = db.get_user(email)
            roster_name = authorized_users.get(email)

            if existing:
                canonical_name = name or existing["name"] or roster_name or "Player"
            else:
                if roster_name is None:
                    st.error("This email is not on the authorized roster. Contact the admin to be added.")
                    return
                canonical_name = roster_name

            db.upsert_user(email=email, name=canonical_name)
            st.session_state["email"] = email
            st.session_state["name"] = canonical_name
            st.success("Signed in!")
            st.rerun()


def hero_header():
    st.markdown(
        """
        <div class="section-card" style="
            display:flex;
            align-items:center;
            gap:.6rem;
        ">
          <div style="font-size:1.8rem; line-height:1;">🏏</div>
          <div>
            <h2 style="margin:0;">IPL Prediction Challenge</h2>
            <div class="muted">Make your picks • Track weekly winners • Climb the leaderboard</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    # If you kept init_db() in Postgres utils, it’s safe to call once.
    try:
        db.init_db()
    except Exception:
        pass

    authorized_users = load_authorized_users()
    hero_header()
    st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)

    if "email" not in st.session_state:
        sign_in(authorized_users)
        return

    current = db.get_user(st.session_state["email"])
    if current:
        st.session_state["name"] = current["name"] or st.session_state.get("name", "Player")

    st.markdown("" \
    "")
    st.success(f"Signed in as {st.session_state['name']} ({st.session_state['email']})")
    st.markdown("" \
    "")
    st.markdown(
        """
        <div class="section-card">
          <b>Next steps</b>
          <ul>
            <li>    Go to <b>🏏 Make Predictions</b> to submit all your picks before the cutoff.</li>
            <li>    Check <b>📊 Leaderboard</b> for season standings.</li>
            <li>    See <b>🗓️ Weekly Winners</b> to celebrate weekly champs.</li>
            <li>    Admins: use <b>🛠️ Admin</b> to upload fixtures/results and set season outcomes.</li>
          </ul>
        </div>
        """, unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()