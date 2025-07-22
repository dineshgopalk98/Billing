import streamlit as st
import pandas as pd

st.set_page_config(page_title="Customer Profiles", page_icon="👤", layout="wide")
st.title("👤 :rainbow[Customer Profiles]")

# Example Profiles Data
if "profiles" not in st.session_state:
    st.session_state.profiles = pd.DataFrame(columns=["Name", "Email", "Phone", "City"])

# Add New Profile
st.subheader("Add Customer Profile")
with st.form("add_profile"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    city = st.text_input("City")
    submitted = st.form_submit_button("Add Profile")
    if submitted and name and email:
        new_profile = pd.DataFrame([[name, email, phone, city]], columns=st.session_state.profiles.columns)
        st.session_state.profiles = pd.concat([st.session_state.profiles, new_profile], ignore_index=True)
        st.success(f"Added profile for {name}")

# Display Profiles
st.subheader("Customer List")
st.dataframe(st.session_state.profiles)
