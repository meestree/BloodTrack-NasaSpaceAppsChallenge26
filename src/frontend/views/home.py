"""Welcome screen matching the supplied Inicio artboard."""

import streamlit as st

from frontend.components.layout import navigate
from frontend.views import login


def render() -> None:
    with st.container(key="landing"):
        st.markdown(
            '<h1 class="welcome-title">WELCOME TO BLOODTRACK</h1>'
            '<p class="welcome-subtitle">Monitoring Health Beyond Earth</p>',
            unsafe_allow_html=True,
        )
        with st.container(key="index_login"):
            login.render(embedded=True)
            st.button("Get started", key="landing_signup", on_click=navigate, args=("signup",))
