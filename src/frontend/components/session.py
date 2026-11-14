"""Login and token state are private to each Streamlit session."""
import streamlit as st

from frontend.services.api import ApiError, request


def clear_session() -> None:
    for key in ('access_token', 'map_date', 'map_date_initialized', 'reliability_dates', 'analysis_dates', 'analysis_metric'):
        st.session_state.pop(key, None)


def require_session() -> str:
    if st.session_state.get('access_token'):
        return st.session_state.access_token
    st.info('Sign in to view your measurements.')
    with st.form('login', clear_on_submit=True):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Sign in')
    if submitted:
        if not username or not password:
            st.error('Enter your username and password.')
        else:
            try:
                with st.spinner('Signing in…'):
                    result = request('POST', '/auth/login', json={'nombre_usuario': username, 'password': password})
                st.session_state.access_token = result['access_token']
                st.rerun()
            except ApiError as error:
                st.error(str(error))
    st.stop()
