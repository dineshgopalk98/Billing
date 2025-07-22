import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime

REG_SHEET_NAME = "Workshop_Registrations"
EQUIP_BUY_AMOUNT = 200

# ---- GSpread -----------------------------------------------------
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
    sh = client.open(REG_SHEET_NAME)
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

def get_user_regs(email):
    df = load_reg_df()
    if df.empty or "Email" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["Email"] == email].copy()

def find_row_for(email, contact, shirt, equip) -> int | None:
    """Find first matching sheet row for the selected registration."""
    sheet = get_sheet()
    # naive strategy: scan all rows (small volume expected)
    vals = sheet.get_all_values()  # list of lists
    # header row at index 0
    for i, row in enumerate(vals[1:], start=2):
        # row -> [Name, Email, Contact, ShirtNeeded, EquipmentChoice, Pending, Timestamp]
        if len(row) < 5:
            continue
        r_email = row[1].strip().lower()
        r_contact = row[2].strip()
        r_shirt = row[3].strip().lower()
        r_equip = row[4].strip().lower()
        if (
            r_email == email.strip().lower() and
            r_contact == str(contact).strip() and
            r_shirt == shirt.strip().lower() and
            r_equip == equip.strip().lower()
        ):
            return i  # 1-based sheet row
    return None

def update_reg(row_num, name, email, contact, shirt, equip):
    sheet = get_sheet()
    pending = EQUIP_BUY_AMOUNT if equip == "Buy" else 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update(f"A{row_num}:G{row_num}", [[name, email, contact, shirt, equip, pending, ts]])

# ---- PAGE --------------------------------------------------------
st.set_page_config(page_title="My Registrations", page_icon="📄", layout="centered")
st.title("📄 My Workshop Registrations")

# Require login
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please log in from the Profile page first.")
    st.stop()

email = st.session_state.user_email
regs = get_user_regs(email)

if regs.empty:
    st.info("No workshop registrations found. Please register first.")
    try:
        st.page_link("pages/2_Workshop_Registration.py", label="🧾 Go to Workshop Registration")
    except Exception:
        pass
    st.stop()

# Show all registrations as cards
st.subheader("Your Registrations")
for idx, row in regs.reset_index(drop=True).iterrows():
    st.markdown(
        f"""
        <div style="
            background-color:#f9f9f9;
            padding:16px;
            margin-bottom:12px;
            border-radius:12px;
            box-shadow:0 1px 4px rgba(0,0,0,0.08);">
            <b>{row['Name']}</b><br>
            Email: {row['Email']}<br>
            Contact: {row['Contact']}<br>
            Shirt Needed: {row['ShirtNeeded']}<br>
            Equipment Choice: {row['EquipmentChoice']}<br>
            Pending Amount: ₹{row['PendingAmount']}
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ---- Edit a specific registration --------------------------------
st.subheader("Edit a Registration")

# Build a label for each reg so user can pick which one to edit
def reg_label(rec):
    return f"{rec['Contact']} | Shirt:{rec['ShirtNeeded']} | Equip:{rec['EquipmentChoice']} | Pending:₹{rec['PendingAmount']}"

regs_reset = regs.reset_index(drop=True)
choice = st.selectbox(
    "Select which registration to edit",
    options=list(regs_reset.index),
    format_func=lambda i: reg_label(regs_reset.iloc[i]),
)

rec = regs_reset.iloc[choice]

with st.form("edit_reg"):
    contact = st.text_input("Contact Number", value=str(rec["Contact"]))
    shirt = st.selectbox(
        "Shirt Needed?",
        ["Yes", "No"],
        index=(0 if rec["ShirtNeeded"] == "Yes" else 1),
    )
    equip = st.selectbox(
        "Equipments Return or Buy?",
        ["Return", "Buy"],
        index=(1 if rec["EquipmentChoice"] == "Buy" else 0),
    )

    if equip == "Buy":
        st.toast(f"💰 You will need to pay ₹{EQUIP_BUY_AMOUNT} during the event.", icon="⚠")

    save_btn = st.form_submit_button("Save Changes", use_container_width=True)
    if save_btn:
        row_num = find_row_for(rec["Email"], rec["Contact"], rec["ShirtNeeded"], rec["EquipmentChoice"])
        if row_num is None:
            st.error("Could not locate this registration row in the sheet.")
        else:
            update_reg(row_num, rec["Name"], rec["Email"], contact.strip(), shirt, equip)
            st.success("Registration updated.")
            st.rerun()

# Back link
try:
    st.page_link("pages/2_Workshop_Registration.py", label="⬅ Back to Workshop Registration")
except Exception:
    pass
