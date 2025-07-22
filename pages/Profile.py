import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import secrets as pysecrets  # stdlib for secure state token

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
st.set_page_config(page_title="Profile / Login", page_icon="👤", layout="centered")

# Load secrets
CLIENT_ID = st.secrets["google"]["client_id"]
CLIENT_SECRET = st.secrets["google"]["client_secret"]
REDIRECT_URI = st.secrets["google"]["redirect_uri"]  # must exactly match what you registered

# Google endpoints
AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = ["openid", "email", "profile"]

# Backend Excel store
USER_FILE = Path("data/users.xlsx")
USER_FILE.parent.mkdir(parents=True, exist_ok=True)
if not USER_FILE.exists():
    pd.DataFrame(columns=["Email", "Name", "Picture"]).to_excel(USER_FILE, index=False)

# Session init
ss = st.session_state
if "logged_in" not in ss:
    ss.logged_in = False
if "user_email" not in ss:
    ss.user_email = None
if "oauth_state" not in ss:
    ss.oauth_state = None

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def load_users():
    return pd.read_excel(USER_FILE)

def save_user(email, name, picture_url=None):
    df = load_users()
    if email not in df["Email"].values:
        new = pd.DataFrame([[email, name, picture_url]], columns=df.columns)
        df = pd.concat([df, new], ignore_index=True)
        df.to_excel(USER_FILE, index=False)
    else:
        # update name/picture if changed
        df.loc[df["Email"] == email, ["Name", "Picture"]] = [name, picture_url]
        df.to_excel(USER_FILE, index=False)

def build_auth_url():
    state_token = pysecrets.token_urlsafe(16)
    ss.oauth_state = state_token
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "redirect_uri": REDIRECT_URI,
        "state": state_token,
        "access_type": "offline",
        "prompt": "select_account",  # or "consent" if you always want re-consent
    }
    from urllib.parse import urlencode
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
    """Check query params for OAuth callback; complete login if present."""
    params = st.query_params.to_dict() if hasattr(st, "query_params") else st.experimental_get_query_params()
    if not params:
        return
    # keys may be lists if using experimental_get_query_params
    code = params.get("code")
    state = params.get("state")

    # Normalize if list
    if isinstance(code, list): code = code[0]
    if isinstance(state, list): state = state[0]

    if code and state:
        if ss.oauth_state and state != ss.oauth_state:
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

        # Persist + mark logged in
        save_user(email, name, picture)
        ss.logged_in = True
        ss.user_email = email

        # Clean query params (avoid re-processing if user refreshes)
        try:
            st.query_params.clear()  # Streamlit >=1.32
        except Exception:
            pass

        st.success(f"Logged in as {name}")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
st.title("👤 Profile / Login")

# Handle OAuth return (if user just came back from Google)
handle_oauth_callback()

if not ss.logged_in:
    st.info("Sign in below to access invoices and personalized features.")
    auth_url = build_auth_url()
    st.link_button("🔐 Sign in with Google", auth_url, use_container_width=True)

    st.caption("We use Google Sign-In only to collect your name & email for your billing profile.")
    st.stop()

# Logged-in view
df_users = load_users()
row = df_users[df_users["Email"] == ss.user_email]
if not row.empty:
    user_name = row.iloc[0]["Name"]
    user_pic = row.iloc[0]["Picture"]
else:
    user_name = ss.user_email
    user_pic = None

# Display profile card
col_a, col_b = st.columns([1,3])
with col_a:
    if user_pic:
        st.image(user_pic, width=96)
    else:
        st.write("🙂")
with col_b:
    st.markdown(f"### {user_name}")
    st.markdown(f"**Email:** {ss.user_email}")

st.divider()

# Allow user to update display name
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


