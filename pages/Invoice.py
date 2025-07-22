import streamlit as st
import pandas as pd

st.title("🧾 Invoice Management")

st.markdown("View and manage all your invoices in one place.")

# Example invoice table
data = {
    "Invoice No": [101, 102, 103],
    "Client": ["ABC Corp", "XYZ Ltd", "PQR Pvt"],
    "Amount (₹)": [5000, 12000, 7500],
    "Status": ["Paid", "Pending", "Pending"]
}
df = pd.DataFrame(data)

st.dataframe(df, use_container_width=True)

