import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

REG_SHEET_NAME = "Workshop_Registrations"
EQUIP_BUY_AMOUNT = 200  # keep consistent w/ Invoice.py

# ------------------------------------------------------------------
# GSpread helpers
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

def get_sheet():
    client = get_gspread_client()
    sh = client.open(REG_SHEET_NAME)  # will error if not shared
    return sh.sheet1

def load_reg_df():
    sheet = get_sheet()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=[
            "Name", "Email", "Contact", "ShirtNeeded",
            "EquipmentChoice", "PendingAmount", "Timestamp"
        ])
    return df

def get_user_reg(email):
    df = load_reg_df()
    if df.empty or "Email" not in df.columns or email not in df["Email"].values:
        return None, None
    rec = df[df["Email"] == email].iloc[0]
    # find row
    sheet = get_sheet()
    cell = sheet.find(email)
    return rec, cell.row

def update_reg(row, name, email, contact, shirt, equip):
    sheet = get_sheet()
    pending = EQUIP_BUY_AMOUNT if equip == "Buy" else 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update(f"A{row}:G{row}", [[name, email, contact, shirt, equip, pending, ts]])

# ------------------------------------------------------------------
# PAGE
# ------------------------------------------------------------------
st.set_page_config(page_title="My Registration", page_icon="📄", layout="centered")
st.title("📄 My Workshop Registration")

# Require login
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in from the Profile page first.")
    st.stop()

email = st.session_state.user_email
rec, row = get_user_reg(email)

if rec is None:
    st.info("No workshop registration found. Go to *Workshop Registration* page to register.")
    try:
        st.page_link("pages/Invoice.py", label="🧾 Go to Workshop Registration")
    except Exception:
        pass
    st.stop()

# Display card
st.markdown(f"### {rec['Name']}")
st.markdown(f"**Email:** {rec['Email']}")
st.markdown(f"**Contact:** {rec['Contact']}")
st.markdown(f"**Shirt Needed:** {rec['ShirtNeeded']}")
st.markdown(f"**Equipment Choice:** {rec['EquipmentChoice']}")
st.markdown(f"**Pending Amount:** ₹{rec['PendingAmount']}")
st.caption(f"Last updated: {rec['Timestamp']}")

st.divider()

# Update toggle
if st.toggle("Edit my registration"):
    with st.form("edit_reg"):
        contact = st.text_input("Contact Number", value=str(rec["Contact"]))
        shirt = st.selectbox("Shirt Needed?", ["Yes", "No"], index=(0 if rec["ShirtNeeded"] == "Yes" else 1))
        equip = st.selectbox("Equipments Return or Buy?", ["Return", "Buy"],
                             index=(1 if rec["EquipmentChoice"] == "Buy" else 0))

        if equip == "Buy":
            st.warning(f"You will need to pay ₹{EQUIP_BUY_AMOUNT} during the event.")
        else:
            st.caption("Return equipment at end of workshop; no charges.")

        save_btn = st.form_submit_button("Save Changes")
        if save_btn:
            update_reg(row, rec["Name"], rec["Email"], contact.strip(), shirt, equip)
            st.success("Registration updated.")
            st.rerun()

# Back link
try:
    st.page_link("pages/Invoice.py", label="⬅ Back to Workshop Registration")
except Exception:
    pass
