"""Registration screen with the exact identification/name fields in the design."""

import streamlit as st

from frontend.components.layout import back_home


def render() -> None:
    with st.form("signup_form", clear_on_submit=True, border=False):
        st.title("Get Started")
        identification = st.text_input("Number of Identification", max_chars=64)
        full_name = st.text_input("Full Name", max_chars=150, autocomplete="name")
        password = st.text_input("Password", type="password", max_chars=128, autocomplete="new-password")
        left, right = st.columns([1.5, 1])
        with left:
            st.checkbox("Remember me", help="Your password and identification are never saved by this form.")
        with right:
            submitted = st.form_submit_button("Sign Up")
    if submitted:
        if not identification.strip() or not full_name.strip() or not password:
            st.error("Complete all three fields.")
        elif len(password) < 12:
            st.error("Use a password with at least 12 characters.")
        else:
            # The backend accepts username/email/birth date, not identification/full name.
            # Do not invent values or falsely report that an account was created.
            st.info("Account registration is not available yet. Please contact your account administrator.")
    st.caption('[Log In](?page=login)')
    back_home()
