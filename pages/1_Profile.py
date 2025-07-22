import streamlit as st
import pandas as pd
import requests
import secrets as pysecrets  # stdlib
import gspread
from google.oauth2.service_account import Credentials

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(page_title="Profile / Login", page_icon="👤", layout="centered")

# Optional debug toggle (sidebar)
DEBUG = st.sidebar.checkbox("Debug mode", False)

def dlog(msg):
    if DEBUG:
        st.write(f"🔧 {msg}")

# ------------------------------------------------------------------
# SECRETS (Google OAuth + Service Account)
# ------------------------------------------------------------------
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]  # exact match to GCP OAuth config

# Google OAuth endpoints
AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = ["openid", "email", "profile"]

# ------------------------------------------------------------------
# GOOGLE SHEET CONFIG
# ------------------------------------------------------------------
# Exact name of your existing Sheet (case sensitive)
SHEET_NAME = "Billing_Users"   # <-- make sure this matches the sheet name in Drive

# ------------------------------------------------------------------
# GOOGLE SHEETS HELPERS
# ------------------------------------------------------------------
def get_gspread_client():
    """Authorize gspread using service account from st.secrets."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(creds)

def get_user_sheet():
    """Open existing Billing_Users sheet by title. Fail clearly if missing."""
    client = get_gspread_client()
    try:
        sh = client.open(SHEET_NAME)  # requires sheet shared w/ service account
    except gspread.SpreadsheetNotFound as e:
        st.error(
            f"Google Sheet '{SHEET_NAME}' not found or not shared with the service "
            "account. Please create it in Drive and share with:\n\n"
            f"`{st.secrets['gcp_service_account']['client_email']}` (Editor)."
        )
        st.stop()
    sheet = sh.sheet1  # use first worksheet
    _ensure_headers(sheet)
    return sheet

def _ensure_headers(sheet):
    """Ensure first row has Email | Name | Picture."""
    # get_all_values() returns list of rows; empty if sheet blank
    vals = sheet.get_all_values()
    if not vals:
        dlog("Sheet empty; writing headers.")
        sheet.update("A1:C1", [["Email", "Name", "Picture"]])
        return
    first = vals[0]
    # pad to length 3
    first = (first + ["", "", ""])[:3]
    if first[0] != "Email" or first[1] != "Name" or first[2] != "Picture":
        dlog("Sheet missing headers; rewriting header row.")
        sheet.update("A1:C1", [["Email", "Name", "Picture"]])

def load_users():
    """Return DataFrame of users. Always has Email/Name/Picture columns."""
    sheet = get_user_sheet()
    records = sheet.get_all_records()  # uses row1 headers
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=["Email", "Name", "Picture"])
    return df

def save_user(email, name, picture_url=None):
    """Insert or update a user in the sheet."""
    sheet = get_user_sheet()
    df = load_users()
    if df.empty or "Email" not in df.columns:
        dlog("No user rows yet; appending first user.")
        sheet.append_row([email, name, picture_url])
        return

    if email not in df["Email"].values:
        dlog(f"Appending new user {email}.")
        sheet.append_row([email, name, picture_url])
    else:
        dlog(f"Updating existing user {email}.")
        cell = sheet.find(email)
        # Update name (col 2) + picture (col 3)
        sheet.update_cell(cell.row, 2, name)
        sheet.update_cell(cell.row, 3, picture_url or "")

# ------------------------------------------------------------------
# OAUTH HELPERS
# ------------------------------------------------------------------
def build_auth_url():
    """Return Google OAuth authorization URL."""
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
    url = f"{AUTH_BASE}?{urlencode(params)}"
    dlog(f"Auth URL built: {url}")
    return url

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
    """If we're returning from Google OAuth, complete login and persist user."""
    params = st.query_params.to_dict() if hasattr(st, "query_params") else st.experimental_get_query_params()
    if not params:
        return
    code = params.get("code")
    state = params.get("state")
    if isinstance(code, list): code = code[0]
    if isinstance(state, list): state = state[0]
    if not code:
        return

    dlog(f"OAuth callback detected. state={state}, code={code[:6]}...")

    if st.session_state.oauth_state and state != st.session_state.oauth_state:
        st.error("OAuth state mismatch. Please try signing in again.")
        return
    try:
        token_data = exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        if not access_token:
            st.error("No access token returned from Google.")
            return
        userinfo = fetch_userinfo(access_token)
    except Exception as e:
        st.error(f"OAuth error: {e}")
        return

    email = userinfo.get("email")
    name = userinfo.get("name", email or "Unknown User")
    picture = userinfo.get("picture")

    dlog(f"Userinfo: email={email}, name={name}")

    # Persist user in Google Sheet
    save_user(email, name, picture)

    # Mark logged in
    st.session_state.logged_in = True
    st.session_state.user_email = email

    # Clear params so we don't reprocess on rerun
    try:
        st.query_params.clear()
    except Exception:
        pass

    st.success(f"Logged in as {name}")

# ------------------------------------------------------------------
# SESSION INIT
# ------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "oauth_state" not in st.session_state:
    st.session_state.oauth_state = None

# ------------------------------------------------------------------
# MAIN UI
# ------------------------------------------------------------------
st.title("👤 Profile / Login")

# Handle Google OAuth return (if any)
handle_oauth_callback()

# Not logged in yet?
if not st.session_state.logged_in:
    st.info("Sign in below to access invoices and personalized features.")
    auth_url = build_auth_url()
    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
    st.stop()

# Logged-in view ---------------------------------------------------
df_users = load_users()
row = df_users[df_users["Email"] == st.session_state.user_email]

if not row.empty:
    user_name = row.iloc[0]["Name"]
    user_pic = row.iloc[0]["Picture"]
else:
    user_name = st.session_state.user_email
    user_pic = None

colA, colB = st.columns([1, 3])
with colA:
    if user_pic:
        st.image(user_pic, width=96)
    else:
        st.write("🙂")
with colB:
    st.markdown(f"### {user_name}")
    st.markdown(f"**Email:** {st.session_state.user_email}")

# Add a clickable link to Workshop Registration
st.page_link("pages/2_Workshop Registration.py", label="Go to Workshop Registration", icon="📝")


st.divider()


# Update display name form
with st.form("update_name"):
    new_name = st.text_input("Update display name", value=user_name or "")
    submitted = st.form_submit_button("Save")
    if submitted:
        save_user(st.session_state.user_email, new_name, user_pic)
        st.success("Profile updated.")
        st.rerun()

# Logout button
if st.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.rerun()
