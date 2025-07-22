import streamlit as st
import pandas as pd

# Page Config
st.set_page_config(page_title="Billing Dashboard", page_icon="📊", layout="wide")

# Title
st.title("📊 Billing Dashboard")

# Login status
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Display login info
if not st.session_state.logged_in:
    st.warning("🔑 Please log in from the **Profile** page to access detailed features like Invoices.")

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
st.area_chart(df_chart.set_index("Month"))

st.caption("Use the sidebar to go to **Profile** and log in for more details.")
