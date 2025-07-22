import streamlit as st

st.title("👤 User Profile")

st.markdown("""
### Dinesh Krishnan
**Email:** dinesh@example.com  
**Company:** Acies Global  
**Role:** Data Scientist
""")

# Profile settings
with st.form("profile_form"):
    name = st.text_input("Name", "Dinesh Krishnan")
    email = st.text_input("Email", "dinesh@example.com")
    submit = st.form_submit_button("Update Profile")
    if submit:
        st.success("Profile updated successfully!")
