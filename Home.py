import streamlit as st
import pandas as pd

# Page Config
st.set_page_config(page_title="Billing Dashboard", page_icon="📊", layout="wide")

# Custom CSS for minimalist design
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }
        h1, h2, h3 {
            font-family: 'Helvetica Neue', sans-serif;
            color: #2c3e50;
        }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Billing Dashboard")

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Invoices", 125)
col2.metric("Revenue (₹)", "₹ 1,25,000")
col3.metric("Outstanding (₹)", "₹ 25,000")

# Graph
st.subheader("Monthly Revenue Trend")
months = ["Jan", "Feb", "Mar", "Apr", "May"]
revenue = [20000, 25000, 22000, 30000, 28000]
df_chart = pd.DataFrame({"Month": months, "Revenue": revenue})
st.area_chart(df_chart.set_index("Month"))

st.caption("Navigate using the sidebar to explore invoices or your profile.")
