import streamlit as st
import pandas as pd
from pathlib import Path

# Backend Excel file
USER_FILE = Path("data/users.xlsx")

# Initialize Excel if not exists
if not USER_FILE.exists():
    df_init = pd.DataFrame(columns=["Email", "Name"])
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_init.to_excel(USER_FILE, index=False)

# Session State for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_email = None

st.title("👤 User Profile")

if not st.session_state.logged_in:
    st.subheader("Login or Register")

    with st.form("login_form"):
        email = st.text_input("Email")
        name = st.text_input("Full Name")
        login_btn = st.form_submit_button("Login / Register")

        if login_btn:
            if email:
                df_users = pd.read_excel(USER_FILE)
                if email not in df_users["Email"].values:
                    # Register new user
                    new_row = pd.DataFrame({"Email": [email], "Name": [name]})
                    df_users = pd.concat([df_users, new_row], ignore_index=True)
                    df_users.to_excel(USER_FILE, index=False)
                    st.success(f"New user registered: {name}")
                else:
                    st.success(f"Welcome back, {name}!")

                st.session_state.logged_in = True
                st.session_state.user_email = email
            else:
                st.error("Please enter a valid email.")
else:
    # Profile details
    df_users = pd.read_excel(USER_FILE)
    user_info = df_users[df_users["Email"] == st.session_state.user_email].iloc[0]
    st.markdown(f"### Hello, {user_info['Name']}")

    # Logout option
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

