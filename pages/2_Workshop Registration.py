import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2 import service_account

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
st.set_page_config(page_title="Workshop Registration", page_icon="🧾", layout="centered")
REG_SHEET_NAME = "Workshop_Registrations"
USER_SHEET_NAME = "Billing_Users"
EQUIP_BUY_AMOUNT = 200  # ₹

# Debug toggle
DEBUG = st.sidebar.checkbox("Debug mode", False)
def dlog(msg):
    if DEBUG:
        st.write(f"🔧 {msg}")

# ------------------------------------------------------------------
# GOOGLE SHEETS CLIENT
# ------------------------------------------------------------------
def get_gspread_client():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)

def _ensure_reg_headers(sheet):
    vals = sheet.get_all_values()
    if not vals:
        sheet.update("A1:G1", [[
            "Name", "Email", "Contact", "ShirtNeeded",
            "EquipmentChoice", "PendingAmount", "Timestamp"
        ]])
        return
    hdr = vals[0] + [""] * 7
    want = ["Name", "Email", "Contact", "ShirtNeeded", "EquipmentChoice", "PendingAmount", "Timestamp"]
    if hdr[:7] != want:
        sheet.update("A1:G1", [want])

def get_sheet(name):
    client = get_gspread_client()
    try:
        sh = client.open(name)
    except gspread.SpreadsheetNotFound:
        st.error(
            f"Google Sheet '{name}' not found or not shared with "
            f"{st.secrets['gcp_service_account']['client_email']} (Editor)."
        )
        st.stop()
    sheet = sh.sheet1
    if name == REG_SHEET_NAME:
        _ensure_reg_headers(sheet)
    return sheet

# ------------------------------------------------------------------
# DATA ACCESS
# ------------------------------------------------------------------
def load_users_df():
    sheet = get_sheet(USER_SHEET_NAME)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=["Email", "Name", "Picture"])
    return df

def load_regs_df():
    sheet = get_sheet(REG_SHEET_NAME)
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=[
            "Name", "Email", "Contact", "ShirtNeeded",
            "EquipmentChoice", "PendingAmount", "Timestamp"
        ])
    return df

def get_user_name(email: str) -> str:
    df = load_users_df()
    if not df.empty and "Email" in df.columns and email in df["Email"].values:
        return df.loc[df["Email"] == email, "Name"].iloc[0]
    return email  # fallback

def get_user_reg(email: str):
    """Return (record_series_or_None, row_number_or_None)."""
    df = load_regs_df()
    if df.empty or "Email" not in df.columns:
        return None, None
    if email not in df["Email"].values:
        return None, None
    rec = df[df["Email"] == email].iloc[0]
    # find row in sheet (add 2 because sheet has header row and df index starts at 0)
    sheet = get_sheet(REG_SHEET_NAME)
    cell = sheet.find(email)
    return rec, cell.row  # row is actual 1-based row in sheet

def upsert_registration(name, email, contact, shirt_needed, equipment_choice):
    sheet = get_sheet(REG_SHEET_NAME)
    rec, row = get_user_reg(email)
    pending = EQUIP_BUY_AMOUNT if equipment_choice == "Buy" else 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if rec is None:
        dlog(f"Appending new registration for {email}")
        sheet.append_row([name, email, contact, shirt_needed, equipment_choice, pending, ts])
    else:
        dlog(f"Updating registration for {email} (row {row})")
        sheet.update(f"A{row}:G{row}", [[name, email, contact, shirt_needed, equipment_choice, pending, ts]])

# ------------------------------------------------------------------
# LOGIN CHECK
# ------------------------------------------------------------------
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in from the Profile page before registering.")
    st.stop()

user_email = st.session_state.user_email
user_name = get_user_name(user_email)

# ------------------------------------------------------------------
# VIEW / UPDATE LINK
# ------------------------------------------------------------------
st.title("🧾 Workshop Registration")

# Check if already registered
existing_reg, _ = get_user_reg(user_email)
if existing_reg is not None:
    st.success("You are already registered.")
    # Clickable link to detail page
    try:
        st.page_link("pages/My_Registration.py", label="📄 View / Update My Registration", icon="📝")
    except Exception:
        # Fallback plain link (user may need to click sidebar)
        st.markdown("**Go to:** *My_Registration* page in sidebar to view/update your registration.*")
else:
    st.info("You are not registered yet. Complete the form below.")

st.divider()

# ------------------------------------------------------------------
# REGISTRATION / UPDATE FORM
# If user is registered, prefill
# ------------------------------------------------------------------
pref_contact = existing_reg["Contact"] if existing_reg is not None else ""
pref_shirt = existing_reg["ShirtNeeded"] if existing_reg is not None else "No"
pref_equip = existing_reg["EquipmentChoice"] if existing_reg is not None else "Return"

with st.form("registration_form"):
    st.write(f"**Name:** {user_name}")
    st.write(f"**Email:** {user_email}")

    contact = st.text_input("Contact Number", value=str(pref_contact) if pref_contact else "")
    shirt_needed = st.selectbox("Shirt Needed?", ["Yes", "No"], index=(0 if pref_shirt == "Yes" else 1))

    equipment_choice = st.selectbox("Equipments return or buy", ["Return", "Buy"])

    # Show a popup notification when 'Buy' is selected
    if equipment_choice == "Buy":
        st.toast("⚠ You will need to pay ₹200 during the event for the equipment.", icon="💰")


    submitted = st.form_submit_button("Register" if existing_reg is None else "Update Registration")

    if submitted:
        if not contact.strip():
            st.error("Please enter your contact number.")
        else:
            upsert_registration(user_name, user_email, contact.strip(), shirt_needed, equipment_choice)
            if existing_reg is None:
                st.success("You have successfully registered for the workshop!")
            else:
                st.success("Your registration has been updated!")
            if equipment_choice == "Buy":
                st.info(f"Please keep ₹{EQUIP_BUY_AMOUNT} ready during the event.")
            st.rerun()
