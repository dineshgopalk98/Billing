import streamlit as st
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="Billing Dashboard", page_icon="📊", layout="wide")

st.title(":rainbow[Billing Dashboard]")
st.write("Welcome to your billing overview.")

# Example Stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Invoices", 125)
with col2:
    st.metric("Revenue (₹)", "₹ 1,25,000")
with col3:
    st.metric("Outstanding (₹)", "₹ 25,000")

# Example Chart
st.subheader("Monthly Revenue Trend")
months = ["Jan", "Feb", "Mar", "Apr", "May"]
revenue = [20000, 25000, 22000, 30000, 28000]
df_chart = pd.DataFrame({"Month": months, "Revenue": revenue})
st.line_chart(df_chart.set_index("Month"))

st.caption("Navigate to other pages using the sidebar: Invoice or Profile.")
