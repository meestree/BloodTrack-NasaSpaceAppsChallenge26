"""Registration using the backend's actual account fields."""
from datetime import date, datetime, timezone
from calendar import monthrange
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
        today = datetime.now(timezone.utc).date()
        st.markdown('<p class="birth-label">Date of birth</p>', unsafe_allow_html=True)
        year_column, month_column, day_column = st.columns(3)
        with year_column:
            year = st.selectbox("Year", range(today.year, 1939, -1), index=None,
                                placeholder="Year", key="birth_year")
        with month_column:
            months = ("January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December")
            month = st.selectbox("Month", range(1, 13), index=None,
                                 format_func=lambda value: months[value - 1],
                                 placeholder="Month", key="birth_month")
        with day_column:
            day = st.selectbox("Day", range(1, 32), index=None,
                               placeholder="Day", key="birth_day")
        birth = None
        birth_message = 'Choose your date of birth.'
        if year is not None and month is not None and day is not None:
            if day > monthrange(year, month)[1]:
                birth_message = 'Choose a valid day for the selected month.'
            elif date(year, month, day) > today:
                birth_message = 'Date of birth cannot be in the future.'
            else:
                birth = date(year, month, day)
        birth_error = st.empty()
        password = st.text_input("Password", type="password", max_chars=128,
                                 autocomplete="new-password")
        password_error = st.empty()
        submitted = st.form_submit_button("Sign Up")
    if submitted:
        fields = {}
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,64}", username.strip()):
            fields['nombre_usuario'] = 'Use 3–64 letters, numbers, or underscores.'
        if not email.strip():
            fields['email'] = 'Enter your email address.'
        if birth is None:
            fields['fecha_nacimiento'] = birth_message
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
    st.button("Log In", key="signup_login", on_click=navigate, args=("login",), type="tertiary")
    back_home()
