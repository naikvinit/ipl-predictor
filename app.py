# app.py
import os
from datetime import datetime, timezone
import streamlit as st
from utils import db_pg as db
from config import APP_TITLE

st.set_page_config(page_title=APP_TITLE, page_icon="🏏", layout="wide")

def sign_in():
    st.markdown(f"### Welcome to **{APP_TITLE}**")
    with st.form("signin"):
        name = st.text_input("Your Name")
        email = st.text_input("Email (used to track your predictions)").lower().strip()
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if not name or not email or "@" not in email:
                st.error("Please enter a valid name and email.")
                return
            db.upsert_user(email=email, name=name)
            st.session_state["email"] = email
            st.session_state["name"] = name
            st.success("Signed in!")
            st.rerun()

def main():
    db.init_db()

    st.title(APP_TITLE)
    st.caption("Submit predictions before the cutoff · Track weekly winners · See the leaderboard")

    # Simple session-based sign-in
    if "email" not in st.session_state:
        sign_in()
    else:
        st.success(f"Signed in as {st.session_state['name']} ({st.session_state['email']})")
        st.markdown("Use the left sidebar to navigate between pages.")

    st.divider()
    st.subheader("Tips")
    st.write(
        "- Make all predictions before the cutoff. After that, the prediction page locks.\n"
        "- Admin can upload fixtures/results and set the final playoff/finalist/champion outcomes.\n"
        "- Leaderboard updates automatically as results are entered."
    )

if __name__ == "__main__":
    main()