import streamlit as st
import pandas as pd
import requests
import secrets as pysecrets  # stdlib secrets
import gspread
from google.oauth2.service_account import Credentials
import hmac, hashlib, base64
from PIL import Image
import io

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(page_title="Profile", page_icon="👤", layout="centered")

# ------------------------------------------------------------------
# CONFIG / SECRETS
# ------------------------------------------------------------------
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]  # must match GCP OAuth
APP_SIGNING_KEY = st.secrets["app"]["signing_key"].encode()  # bytes

AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = ["openid", "email", "profile"]

SHEET_NAME = "Billing_Users"  # case sensitive

# ------------------------------------------------------------------
# SMALL UTILS
# ------------------------------------------------------------------
def sign_email(email: str) -> str:
    """Return URL-safe HMAC signature for email."""
    digest = hmac.new(APP_SIGNING_KEY, email.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")

def check_signature(email: str, token: str) -> bool:
    """Constant-time check."""
    expected = sign_email(email)
    # pad token for base64 lengths? we trimmed =; so compare raw
    return hmac.compare_digest(expected, token)

def set_remember_me(email: str):
    """Write email + signed token into URL query params so we can auto-login later."""
    token = sign_email(email)
    try:
        st.query_params.update({"u": email, "t": token})
    except Exception:
        pass  # ignore if running older Streamlit

def clear_remember_me():
    try:
        st.query_params.clear()
    except Exception:
        pass

# ------------------------------------------------------------------
# GOOGLE SHEETS
# ------------------------------------------------------------------
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)

def _ensure_headers(sheet):
    vals = sheet.get_all_values()
    if not vals:
        sheet.update("A1:C1", [["Email", "Name", "Picture"]])
        return
    hdr = (vals[0] + ["", "", ""])[:3]
    if hdr != ["Email", "Name", "Picture"]:
        sheet.update("A1:C1", [["Email", "Name", "Picture"]])

def get_user_sheet():
    client = get_gspread_client()
    try:
        sh = client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        st.error(
            f"Google Sheet '{SHEET_NAME}' not found or not shared with the service "
            f"account:\n\n`{st.secrets['gcp_service_account']['client_email']}` (Editor)."
        )
        st.stop()
    sheet = sh.sheet1
    _ensure_headers(sheet)
    return sheet

@st.cache_data(ttl=60)
def load_users():
    sheet = get_user_sheet()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=["Email", "Name", "Picture"])
    return df

def save_user(email, name, picture_url=None):
    sheet = get_user_sheet()
    df = load_users()
    if df.empty or "Email" not in df.columns or email not in df["Email"].values:
        sheet.append_row([email, name, picture_url])
        load_users.clear()  # invalidate cache
    else:
        cell = sheet.find(email)
        sheet.update_cell(cell.row, 2, name)
        sheet.update_cell(cell.row, 3, picture_url or "")
        load_users.clear()

# ------------------------------------------------------------------
# GOOGLE OAUTH HELPERS
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
        "prompt": "select_account",  # show account picker
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
    """If returning from Google, complete the login."""
    params = (
        st.query_params.to_dict()
        if hasattr(st, "query_params")
        else st.experimental_get_query_params()
    )
    code = params.get("code")
    state = params.get("state")
    if isinstance(code, list): code = code[0]
    if isinstance(state, list): state = state[0]
    if not code:
        return
    # state check
    if st.session_state.oauth_state and state != st.session_state.oauth_state:
        st.error("OAuth state mismatch. Please try again.")
        return
    # token exchange
    try:
        token_data = exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        if not access_token:
            st.error("No access token from Google.")
            return
        userinfo = fetch_userinfo(access_token)
    except Exception as e:
        st.error(f"OAuth error: {e}")
        return
    email = userinfo.get("email")
    name = userinfo.get("name", email or "Unknown User")
    picture = userinfo.get("picture")

    # persist to sheet
    save_user(email, name, picture)

    # set session + remember token
    st.session_state.logged_in = True
    st.session_state.user_email = email
    set_remember_me(email)  # <-- persists in URL

    # clear OAuth params so they don't re-trigger
    try:
        st.query_params.update({"u": email, "t": sign_email(email)})
        st.query_params.pop("code", None)
        st.query_params.pop("state", None)
    except Exception:
        pass

    st.success(f"Logged in as {name}")

# ------------------------------------------------------------------
# AUTO-LOGIN FROM SIGNED QUERY PARAMS
# ------------------------------------------------------------------
def try_auto_login_from_query():
    """If ?u=email&t=token present and valid, mark logged_in without OAuth."""
    params = (
        st.query_params.to_dict()
        if hasattr(st, "query_params")
        else st.experimental_get_query_params()
    )
    email = params.get("u")
    token = params.get("t")
    if isinstance(email, list): email = email[0]
    if isinstance(token, list): token = token[0]
    if not email or not token:
        return
    if not check_signature(email, token):
        return
    # confirm email actually exists in Billing_Users sheet
    df = load_users()
    if "Email" in df.columns and email in df["Email"].values:
        st.session_state.logged_in = True
        st.session_state.user_email = email

# ------------------------------------------------------------------
# SESSION INIT
# ------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "oauth_state" not in st.session_state:
    st.session_state.oauth_state = None

# Try auto-login BEFORE rendering UI
if not st.session_state.logged_in:
    try_auto_login_from_query()

# Handle Google OAuth callback (may override the above)
handle_oauth_callback()

# ------------------------------------------------------------------
# HEADER ROW WITH LOGOUT BUTTON (top-right)
# ------------------------------------------------------------------
hdr_l, spacer, hdr_r = st.columns([5,2,1])
with hdr_l:
    st.title("👤 Profile")
with spacer:
    st.write("")
with hdr_r:
    st.write("")
    if st.button("Logout", key="logout_button_top"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        clear_remember_me()
        st.rerun()

# ------------------------------------------------------------------
# NOT LOGGED IN? SHOW LOGIN BUTTON
# ------------------------------------------------------------------
if not st.session_state.logged_in:
    st.info("Sign in below to access workshop registration!!")
    auth_url = build_auth_url()
    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)
    st.stop()

# ------------------------------------------------------------------
# LOGGED-IN VIEW
# ------------------------------------------------------------------
df_users = load_users()
row = df_users[df_users["Email"] == st.session_state.user_email]

if not row.empty:
    user_name = row.iloc[0]["Name"]
    user_pic = row.iloc[0]["Picture"]
else:
    user_name = st.session_state.user_email
    user_pic = None

# Profile card
colA, colB, spacer1, spacer2 = st.columns([1,4,2,1])
with colA:
    if user_pic:
        st.image(user_pic, width=100)
    else:
        st.write("🙂")
# Compact profile display row ---------------------------------------

with colB:
    # Small font name + email
    st.markdown(
        f"<p style='font-size:16px; font-weight:600; margin-bottom:2px;'>{user_name}</p>"
        f"<p style='font-size:13px; color:gray; margin-top:0;'>{st.session_state.user_email}</p>",
        unsafe_allow_html=True
    )

with spacer1:
    st.write("")
with spacer2:
    # Tiny pencil popover trigger
    with st.popover("✏", use_container_width=True):
        st.markdown("Edit profile")  # small heading in the popover

        # Editable name
        new_name = st.text_input(
            "Name", 
            value=user_name, 
            key="profile_edit_name"  # hide full label
        )
  # lightweight label substitute

        # Editable contact (if you track contact in session or sheet)
        new_contact = st.text_input(
            "Contact", 
            value=st.session_state.get("user_contact", ""), 
            key="profile_edit_contact"
        )


        # Optional: upload profile pic (jpeg/png)
        new_pic_file = st.file_uploader(
            "Profile Pic", 
            type=["jpg", "jpeg", "png"], 
            key="profile_edit_pic"        )


        save_clicked = st.button("Save", key="profile_edit_save_btn", use_container_width=True)
        if save_clicked:
            # Handle picture -> bytes -> maybe upload/store URL (see below)
            pic_url = user_pic  # default to existing
            if new_pic_file is not None:
                # For now: display only (no persistence to remote store yet)
                img_bytes = new_pic_file.read()
                st.session_state.user_pic_bytes = img_bytes
                # If storing to Google Drive or S3, do it here and set pic_url to that location.
                pic_url = None  # or updated location

            # Persist changes: update sheet for name; contact not yet in Billing_Users schema
            save_user(st.session_state.user_email, new_name, pic_url)
            st.session_state.user_name = new_name
            st.session_state.user_contact = new_contact  # session only unless you persist

            st.success("Profile updated.")
            st.rerun()
# Navigation to Workshop Registration (internal page)
# Use st.page_link if available; fallback markdown

st.divider()

# ------------------------------------------------------------------
# NAME UPDATE FORM
# ------------------------------------------------------------------


st.page_link("pages/2_Workshop Registration.py", label="Go to Workshop Registration", icon="📝")

