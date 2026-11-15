"""Login page matching the black background and red card in the screenshots."""

import streamlit as st

from frontend.components.layout import back_home, navigate


def start_login() -> None:
    """Switch pages before doing network or password verification work."""
    username = st.session_state.get('login_username', '').strip()
    password = st.session_state.get('login_password', '')
    if not username or not password:
        st.session_state['login_error'] = 'Enter your user and password.'
        return
    st.session_state['_pending_login'] = (username, password, st.session_state.get('login_remember', False))
    navigate('loading')


def render(embedded: bool = False) -> None:
    if error := st.session_state.pop('login_error', None):
        st.error(error)
    if notice := st.session_state.pop("signup_notice", None):
        st.success(notice)
    if notice := st.session_state.pop("logout_notice", None):
        st.warning(notice)
    if st.session_state.get("access_token"):
        navigate("welcome")
        st.rerun()

    with st.form("login_form", clear_on_submit=True, border=False, enter_to_submit=True):
        st.title("Log In")
        st.text_input("User", value=st.session_state.get("remembered_user", ""), max_chars=64, autocomplete="username", key="login_username")
        st.text_input("Password", type="password", max_chars=128, autocomplete="current-password", key="login_password")
        with st.container(key="login_actions"):
            remember_column, submit_column = st.columns([1.2, 1])
            with remember_column:
                st.checkbox("Remember me", help="Remember your username during this browser session.", key="login_remember")
            with submit_column:
                st.form_submit_button("Log In", on_click=start_login)
    if not embedded:
        st.button("Sign Up", key="login_signup", on_click=navigate, args=("signup",), type="tertiary")
        back_home()
