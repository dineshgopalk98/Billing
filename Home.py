import streamlit as st

# ---------------------------
# Page Configuration
# ---------------------------
st.set_page_config(page_title="Embroidery Workshop", page_icon="🧵", layout="centered")

# Hide menu & footer
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# ---------------------------
# Landing Page Content
# ---------------------------
st.title("🧵 Welcome to Registration page of the Embroidery Workshop!")
st.markdown(
    """
    ### Discover the art of embroidery!
    Join our **exclusive embroidery workshop** where you’ll learn:
    - The basics of hand embroidery techniques.
    - How to stitch patters on any fabric of your choice.
    - Creating your own beautiful design during the session on a T-shirt.

    **Date:** 23rd August 2025  
    **Venue:** Ikigai, Velachery, Chennai  
    **Registration Fee:** ₹800 (includes materials)
    """
)

st.info("To register for this workshop, you need to login with your Google account.")

# Navigation to Profile Page
if st.button("🔐 Login to Register"):
    st.switch_page("pages/1_Profile.py")

# Footer note
st.caption("Crafted with ❤️ by The Broderie Studio Workshop Team.")
