"""Registration using the backend's actual account fields."""
from datetime import date, datetime, timezone
import re

import streamlit as st

from frontend import api
from frontend.components.layout import back_home, navigate


def render() -> None:
    with st.form("signup_form", clear_on_submit=False, border=False):
        st.title("Get Started")
        username = st.text_input("Username", max_chars=64, autocomplete="username")
        username_error = st.empty()
        email = st.text_input("Email", max_chars=254, autocomplete="email")
        email_error = st.empty()
        birth = st.date_input("Date of birth", value=None, min_value=date(1900, 1, 1),
                              max_value=datetime.now(timezone.utc).date(), format="YYYY-MM-DD")
        birth_error = st.empty()
        password = st.text_input("Password", type="password", max_chars=128,
                                 autocomplete="new-password", help="Use 12–128 characters.")
        password_error = st.empty()
        submitted = st.form_submit_button("Sign Up")
    if submitted:
        fields = {}
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,64}", username.strip()):
            fields['nombre_usuario'] = 'Use 3–64 letters, numbers, or underscores.'
        if not email.strip():
            fields['email'] = 'Enter your email address.'
        if birth is None:
            fields['fecha_nacimiento'] = 'Choose your date of birth.'
        if len(password) < 12:
            fields['password'] = 'Use a password with at least 12 characters.'
        if not fields:
            try:
                with st.spinner('Creating your account…'):
                    api.request('POST', '/auth/register', json={
                        'nombre_usuario': username.strip(), 'email': email.strip(),
                        'fecha_nacimiento': birth.isoformat(), 'password': password,
                    })
                st.session_state['signup_notice'] = 'Account created. Log in to continue.'
                navigate('login')
                st.rerun()
            except api.ApiError as error:
                fields = error.fields
                st.error(str(error))
        for name, placeholder in {'nombre_usuario': username_error, 'email': email_error,
                                   'fecha_nacimiento': birth_error, 'password': password_error}.items():
            if name in fields:
                placeholder.error(fields[name])
    st.caption('[Log In](?page=login)')
    back_home()
