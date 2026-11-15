"""Private Streamlit session state and one authentication/error flow for all pages."""
import streamlit as st

from frontend.api import ApiError, close_client
from frontend.components.layout import navigate


SESSION_KEYS = (
    'access_token', 'user', 'drawer_is_open', 'map_date', 'map_date_initialized',
    'reliability_dates', 'analysis_dates', 'analysis_metric',
    'reliability_complete_dates', 'analysis_complete_dates',
)


def clear_session() -> None:
    close_client()
    for key in list(st.session_state):
        if key in SESSION_KEYS or key.startswith(('measure_', 'history_', 'daily_', 'period_')):
            st.session_state.pop(key, None)


def require_session() -> str:
    if st.session_state.get('access_token'):
        return st.session_state.access_token
    st.session_state['logout_notice'] = 'Please log in to view your measurements.'
    navigate('login')
    st.rerun()


def show_api_error(error: ApiError) -> None:
    if error.status == 401:
        clear_session()
        st.session_state['logout_notice'] = str(error)
        navigate('login')
        st.rerun()
    st.error(str(error))
