import streamlit as st
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials
import secrets as pysecrets  # for secure state token

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
st.set_page_config(page_title="Profile / Login", page_icon="👤", layout="centered")

# Load secrets for Google OAuth
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]

# Google endpoints
AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = ["openid", "email", "profile"]

# Google Sheets Config
SHEET_NAME = "Billing Users"  # Must be created in Google Sheets

# ------------------------------------------------------------------
# Google Sheets Helper Functions
# ------------------------------------------------------------------
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

def get_user_sheet():
    client = get_gspread_client()
    return client.open(SHEET_NAME).sheet1

def load_users():
    sheet = get_user_sheet()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_user(email, name, picture_url=None):
    sheet = get_user_sheet()
    df = load_users()
    if email not in df["Email"].values:
        sheet.append_row([email, name, picture_url])
    else:
        # Update name/picture if changed
        cell = sheet.find(email)
        if cell:
            row_num = cell.row
            sheet.update(f"B{row_num}:C{row_num}", [[name, picture_url]])

# ------------------------------------------------------------------
# OAuth Helper Functions
# ------------------------------------------------------------------
def build_auth_url():
    state_token = pysecrets.token_urlsafe(16)
    st.session_state.oauth_state = state_token
    from urllib.parse import urlencode
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "redirect_uri": REDIRECT_URI,
        "state": state_token,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{AUTH_BASE}?{urlencode(params)}"

def exchange_code_for_tokens(code):
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()

def fetch_userinfo(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(USERINFO_URL, headers=headers)
    resp.raise_for_status()
    return resp.json()

def handle_oauth_callback():
    params = st.query_params.to_dict() if hasattr(st, "query_params") else st.experimental_get_query_params()
    if not params:
        return
    code = params.get("code")
    state = params.get("state")
    if isinstance(code, list): code = code[0]
    if isinstance(state, list): state = state[0]
    if code and state:
        if st.session_state.oauth_state and state != st.session_state.oauth_state:
            st.error("OAuth state mismatch. Try again.")
            return
        try:
            token_data = exchange_code_for_tokens(code)
            access_token = token_data.get("access_token")
            if not access_token:
                st.error("No access token returned.")
                return
            userinfo = fetch_userinfo(access_token)
        except Exception as e:
            st.error(f"OAuth error: {e}")
            return

        email = userinfo.get("email")
        name = userinfo.get("name", email or "Unknown User")
        picture = userinfo.get("picture")

        save_user(email, name, picture)
        st.session_state.logged_in = True
        st.session_state.user_email = email

        try:
            st.query_params.clear()
        except Exception:
            pass
        st.success(f"Logged in as {name}")

# ------------------------------------------------------------------
# Session Initialization
# ------------------------------------------------------------------
ss = st.session_state
if "logged_in" not in ss:
    ss.logged_in = False
if "user_email" not in ss:
    ss.user_email = None
if "oauth_state" not in ss:
    ss.oauth_state = None

# ------------------------------------------------------------------
# Main UI
# ------------------------------------------------------------------
st.title("👤 Profile / Login")
handle_oauth_callback()

if not ss.logged_in:
    st.info("Sign in below to access invoices and personalized features.")
    auth_url = build_auth_url()
    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
    st.stop()

# Logged-in View
df_users = load_users()
row = df_users[df_users["Email"] == ss.user_email]
if not row.empty:
    user_name = row.iloc[0]["Name"]
    user_pic = row.iloc[0]["Picture"]
else:
    user_name = ss.user_email
    user_pic = None

col_a, col_b = st.columns([1, 3])
with col_a:
    if user_pic:
        st.image(user_pic, width=96)
    else:
        st.write("🙂")
with col_b:
    st.markdown(f"### {user_name}")
    st.markdown(f"**Email:** {ss.user_email}")

st.divider()

# Update display name
with st.form("update_name"):
    new_name = st.text_input("Update display name", value=user_name or "")
    submitted = st.form_submit_button("Save")
    if submitted:
        save_user(ss.user_email, new_name, user_pic)
        st.success("Profile updated.")
        st.rerun()

# Logout
if st.button("Logout"):
    ss.logged_in = False
    ss.user_email = None
    st.rerun()



