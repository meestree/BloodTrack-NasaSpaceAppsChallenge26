"""Login page matching the black background and red card in the screenshots."""

import streamlit as st

from frontend import api
from frontend.components.layout import back_home, navigate


def render(embedded: bool = False) -> None:
    if notice := st.session_state.pop("signup_notice", None):
        st.success(notice)
    if notice := st.session_state.pop("logout_notice", None):
        st.warning(notice)
    if st.session_state.get("access_token"):
        navigate("welcome")
        st.rerun()

    with st.form("login_form", clear_on_submit=True, border=False):
        st.title("Log In")
        username = st.text_input("User", value=st.session_state.get("remembered_user", ""), max_chars=64, autocomplete="username")
        password = st.text_input("Password", type="password", max_chars=128, autocomplete="current-password")
        with st.container(key="login_actions"):
            remember_column, submit_column = st.columns([1.2, 1])
            with remember_column:
                remember = st.checkbox("Remember me", help="Remember your username during this browser session.")
            with submit_column:
                submitted = st.form_submit_button("Log In")
    if submitted:
        if not username.strip() or not password:
            st.error("Enter your user and password.")
        else:
            try:
                with st.spinner("Signing in…"):
                    token, user = api.login(username.strip(), password)
                st.session_state["access_token"] = token
                st.session_state["user"] = user
                if remember:
                    st.session_state["remembered_user"] = username.strip()
                else:
                    st.session_state.pop("remembered_user", None)
                navigate("welcome")
                st.rerun()
            except api.ApiError as error:
                st.error(str(error))
    if not embedded:
        st.button("Sign Up", key="login_signup", on_click=navigate, args=("signup",), type="tertiary")
        back_home()
