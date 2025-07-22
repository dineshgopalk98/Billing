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
    want = ["Name", "Email", "Contact", "ShirtNeeded", "EquipmentChoice", "PendingAmount", "Timestamp"]
    hdr = (vals[0] + [""] * len(want))[:len(want)]
    if hdr != want:
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

def get_user_regs(email: str) -> pd.DataFrame:
    """All registrations for this email."""
    df = load_regs_df()
    if df.empty or "Email" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["Email"] == email].copy()

def get_latest_user_reg(email: str):
    """Most recent reg (last row in sheet for email)."""
    regs = get_user_regs(email)
    if regs.empty:
        return None
    # since sheet.get_all_records preserves order, last occurrence is latest
    return regs.iloc[-1]

def reg_exists_exact(name, email, contact, shirt_needed, equipment_choice) -> bool:
    """Check for exact duplicate (case-insensitive, contact stripped)."""
    df = load_regs_df()
    if df.empty: 
        return False
    # normalize
    name = (name or "").strip().lower()
    email = (email or "").strip().lower()
    contact = (str(contact) or "").strip()
    shirt_needed = (shirt_needed or "").strip().lower()
    equipment_choice = (equipment_choice or "").strip().lower()

    df_cmp = pd.DataFrame({
        "Name": df["Name"].astype(str).str.strip().str.lower(),
        "Email": df["Email"].astype(str).str.strip().str.lower(),
        "Contact": df["Contact"].astype(str).str.strip(),
        "ShirtNeeded": df["ShirtNeeded"].astype(str).str.strip().str.lower(),
        "EquipmentChoice": df["EquipmentChoice"].astype(str).str.strip().str.lower(),
    })
    mask = (
        (df_cmp["Name"] == name) &
        (df_cmp["Email"] == email) &
        (df_cmp["Contact"] == contact) &
        (df_cmp["ShirtNeeded"] == shirt_needed) &
        (df_cmp["EquipmentChoice"] == equipment_choice)
    )
    return mask.any()

def append_registration(name, email, contact, shirt_needed, equipment_choice):
    """Always append a new row."""
    sheet = get_sheet(REG_SHEET_NAME)
    pending = EQUIP_BUY_AMOUNT if equipment_choice == "Buy" else 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([name, email, contact, shirt_needed, equipment_choice, pending, ts])

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

user_regs = get_user_regs(user_email)
latest_reg = get_latest_user_reg(user_email)

if not user_regs.empty:
    st.success("You have existing registration(s).")
    try:
        st.page_link("pages/3_My_Registration.py", label="View / Update My Registrations", icon="📝")
    except Exception:
        st.markdown("**Go to:** *My Registrations* page in sidebar to view/update.")
else:
    st.info("You are not registered yet. Complete the form below.")

st.divider()

# Prefill from latest reg (if any)
pref_name = latest_reg["Name"] if latest_reg is not None else user_name
pref_contact = latest_reg["Contact"] if latest_reg is not None else ""
pref_shirt = latest_reg["ShirtNeeded"] if latest_reg is not None else "No"
pref_equip = latest_reg["EquipmentChoice"] if latest_reg is not None else "Return"

# ------------------------------------------------------------------
# FORM
# ------------------------------------------------------------------
with st.form("registration_form"):
    name_input = st.text_input("Full Name", value="")
    mail_input = st.text_input("Email",value=user_email)

    contact = st.text_input("Contact Number", value="")
    shirt_needed = st.selectbox("Shirt Needed?", ["Yes", "No"], index=(0 if pref_shirt == "Yes" else 1))
    equipment_choice = st.selectbox("Equipments return or buy", ["Return", "Buy"],
                                    index=(1 if pref_equip == "Buy" else 0))

    # Live popup
    if equipment_choice == "Buy":
        st.toast(f"⚠ You will need to pay ₹{EQUIP_BUY_AMOUNT} during the event.", icon="💰")

    submitted = st.form_submit_button("Register")

    if submitted:
        if not contact.strip():
            st.error("Please enter your contact number.")
        else:
            # Duplicate check
            if reg_exists_exact(name_input.strip(), user_email, contact, shirt_needed, equipment_choice):
                st.error("User with same details already exists.")
            else:
                append_registration(name_input.strip(), user_email, contact.strip(), shirt_needed, equipment_choice)
                st.success("Registration saved!")
                if equipment_choice == "Buy":
                    st.info(f"Please keep ₹{EQUIP_BUY_AMOUNT} ready during the event.")
                st.rerun()
