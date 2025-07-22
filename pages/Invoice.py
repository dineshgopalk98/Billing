import streamlit as st
import pandas as pd
from datetime import datetime

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.error("🔐 Please log in from the Profile page to access Invoices.")
    st.stop()

st.title("🧾 Invoice Management")

st.set_page_config(page_title="Create Invoice", page_icon="🧾", layout="wide")
st.title("🧾 :rainbow[Invoice Generator]")

# Customer Info
st.subheader("Customer Information")
col1, col2 = st.columns(2)
with col1:
    customer_name = st.text_input("Customer Name")
    customer_email = st.text_input("Customer Email")
with col2:
    invoice_date = st.date_input("Invoice Date", datetime.today())
    due_date = st.date_input("Due Date", datetime.today())

# Item Details
st.subheader("Add Items")
items = []
item_count = st.number_input("Number of items", min_value=1, value=1)
for i in range(item_count):
    with st.expander(f"Item {i+1}"):
        item = st.text_input(f"Item {i+1} Name", key=f"name_{i}")
        qty = st.number_input(f"Quantity {i+1}", min_value=1, value=1, key=f"qty_{i}")
        price = st.number_input(f"Price {i+1}", min_value=0.0, value=0.0, key=f"price_{i}")
        total = qty * price
        items.append({"Item": item, "Quantity": qty, "Unit Price": price, "Total": total})

df_items = pd.DataFrame(items)

# Invoice Summary
st.subheader("Summary")
tax = st.slider("Tax (%)", 0, 28, 18)
discount = st.number_input("Discount", min_value=0.0, value=0.0)
subtotal = df_items["Total"].sum()
tax_amount = subtotal * (tax / 100)
grand_total = subtotal + tax_amount - discount

st.metric("Grand Total", f"₹ {grand_total:,.2f}")

# Generate Invoice
if st.button("Generate Invoice"):
    st.success("Invoice generated successfully!")
    st.balloons()
    st.dataframe(df_items)
    csv = df_items.to_csv(index=False).encode("utf-8")
    st.download_button("Download Invoice CSV", csv, "invoice.csv", "text/csv")


