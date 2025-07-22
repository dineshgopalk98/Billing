import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account


if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("🔐 Please log in from the Profile page to access Invoices.")
    st.stop()

# -------------------------------
# Google Sheet Setup
# -------------------------------
REG_SHEET_NAME = "Workshop_Registrations"
USER_SHEET_NAME = "Billing_Users"

# Authenticate Google Sheets
def get_gspread_client():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(credentials)

def get_sheet(name):
    client = get_gspread_client()
    try:
        return client.open(name).sheet1
    except gspread.SpreadsheetNotFound:
        st.error(f"Google Sheet '{name}' not found.")
        return None

def load_registrations():
    sheet = get_sheet(REG_SHEET_NAME)
    if sheet:
        records = sheet.get_all_records()
        return pd.DataFrame(records)
    return pd.DataFrame()

def save_registration(data):
    sheet = get_sheet(REG_SHEET_NAME)
    if sheet:
        sheet.append_row(data)

def get_user_details(email):
    sheet = get_sheet(USER_SHEET_NAME)
    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        if email in df["Email"].values:
            return df[df["Email"] == email].iloc[0]["Name"]
    return "Unknown User"

# -------------------------------
# UI Components
# -------------------------------
st.set_page_config(page_title="Workshop Registration", page_icon="🧾", layout="centered")
st.title("🧾 Workshop Registration")

# Ensure user is logged in
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in from the Profile page before registering.")
    st.stop()

# Fetch user details
user_email = st.session_state.user_email
user_name = get_user_details(user_email)

# -------------------------------
# View My Registration
# -------------------------------
st.subheader("📄 My Current Registration")
df_reg = load_registrations()

if not df_reg.empty and user_email in df_reg["Email"].values:
    user_reg = df_reg[df_reg["Email"] == user_email]
    st.success("You have already registered for this workshop.")
    st.table(user_reg)
else:
    st.info("You have not registered yet.")

st.divider()

# -------------------------------
# Registration Form
# -------------------------------
with st.form("registration_form"):
    st.write(f"**Name:** {user_name}")
    st.write(f"**Email:** {user_email}")

    contact = st.text_input("Contact Number")
    shirt_needed = st.selectbox("Shirt Needed?", ["Yes", "No"])
    equipment_choice = st.selectbox("Equipments Return or Buy?", ["Return", "Buy"])

    if equipment_choice == "Buy":
        st.warning("You will need to pay ₹200 during the event for the equipment.")

    submitted = st.form_submit_button("Register Now")

    if submitted:
        if not contact:
            st.error("Please enter your contact number.")
        else:
            data = [user_name, user_email, contact, shirt_needed, equipment_choice, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
            save_registration(data)
            st.success("You have successfully registered for the workshop!")
            if equipment_choice == "Buy":
                st.info("Please keep ₹200 ready during the event.")
            st.rerun()



