"""Immediate sign-in screen, displayed before authentication starts."""
import streamlit as st

from frontend import api
from frontend.components.layout import navigate


def render() -> None:
    pending = st.session_state.pop('_pending_login', None)
    if pending is None:
        navigate('welcome' if st.session_state.get('access_token') else 'login')
        st.rerun()

    st.html('''
        <section class="login-loading" role="status" aria-live="polite">
            <div class="login-loading-card">
                <span class="login-loading-spinner" aria-hidden="true"></span>
                <h1>Signing in…</h1>
                <p>Welcome to BloodTrack</p>
            </div>
        </section>
    ''')
    username, password, remember = pending
    # Consume pending credentials once; never put them in a URL or a cache.
    st.session_state.pop('login_password', None)
    try:
        token, user = api.login(username, password)
    except api.ApiError as error:
        st.session_state['login_error'] = str(error)
        navigate('login')
    else:
        st.session_state['access_token'] = token
        st.session_state['user'] = user
        if remember:
            st.session_state['remembered_user'] = username
        else:
            st.session_state.pop('remembered_user', None)
        navigate('welcome')
    st.rerun()
