import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import secrets as pysecrets
import gspread
from google.oauth2.service_account import Credentials

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
st.set_page_config(page_title="Profile / Login", page_icon="👤", layout="centered")

# Google OAuth client details
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]

AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = ["openid", "email", "profile"]

# Google Sheets
SHEET_NAME = "Billing_Users"

# ------------------------------------------------------------------
# Google Sheets Helpers
# ------------------------------------------------------------------
def get_gspread_client():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets client: {e}")
        st.stop()

def get_user_sheet():
    client = get_gspread_client()
    try:
        return client.open(SHEET_NAME).sheet1
    except gspread.SpreadsheetNotFound:
        st.warning("Google Sheet not found. Creating a new one...")
        sh = client.create(SHEET_NAME)
        sh.share(st.secrets["gcp_service_account"]["client_email"], perm_type="user", role="writer")
        sheet = sh.sheet1
        sheet.append_row(["Email", "Name", "Picture"])
        return sheet
    except Exception as e:
        st.error(f"Error accessing Google Sheet: {e}")
        st.stop()

def load_users():
    sheet = get_user_sheet()
    records = sheet.get_all_records()
    return pd.DataFrame(records)

def save_user(email, name, picture_url=None):
    sheet = get_user_sheet()
    df = load_users()
    if email not in df["Email"].values:
        sheet.append_row([email, name, picture_url])
    else:
        cell = sheet.find(email)
        sheet.update_cell(cell.row, 2, name)
        sheet.update_cell(cell.row, 3, picture_url or "")

# ------------------------------------------------------------------
# OAuth Helpers
# ------------------------------------------------------------------
def build_auth_url():
    state_token = pysecrets.token_urlsafe(16)
    st.session_state.oauth_state = state_token
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "redirect_uri": REDIRECT_URI,
        "state": state_token,
        "access_type": "offline",
        "prompt": "select_account"
    }
    from urllib.parse import urlencode
    return f"{AUTH_BASE}?{urlencode(params)}"

def exchange_code_for_tokens(code):
    data = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
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
            st.error("OAuth state mismatch.")
            return
        try:
            token_data = exchange_code_for_tokens(code)
            access_token = token_data.get("access_token")
            if not access_token:
                st.error("No access token.")
                return
            userinfo = fetch_userinfo(access_token)
        except Exception as e:
            st.error(f"OAuth error: {e}")
            return

        email = userinfo.get("email")
        name = userinfo.get("name", email)
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
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "oauth_state" not in st.session_state:
    st.session_state.oauth_state = None

# ------------------------------------------------------------------
# Main UI
# ------------------------------------------------------------------
st.title("👤 Profile / Login")
handle_oauth_callback()

if not st.session_state.logged_in:
    st.info("Sign in below to access invoices and personalized features.")
    auth_url = build_auth_url()
    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
    st.stop()

# Display user profile
df_users = load_users()
user_row = df_users[df_users["Email"] == st.session_state.user_email]
user_name = user_row.iloc[0]["Name"] if not user_row.empty else st.session_state.user_email
user_pic = user_row.iloc[0]["Picture"] if not user_row.empty else None

col1, col2 = st.columns([1, 3])
with col1:
    st.image(user_pic, width=96) if user_pic else st.write("🙂")
with col2:
    st.markdown(f"### {user_name}")
    st.markdown(f"**Email:** {st.session_state.user_email}")

st.divider()
with st.form("update_name"):
    new_name = st.text_input("Update display name", value=user_name or "")
    submitted = st.form_submit_button("Save")
    if submitted:
        save_user(st.session_state.user_email, new_name, user_pic)
        st.success("Profile updated.")
        st.rerun()

if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.rerun()




