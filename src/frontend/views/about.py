"""Public About Us page with the team's vision and application features."""
import streamlit as st

from frontend.components.layout import back_home
from frontend.views.information import render_about


def render() -> None:
    with st.container(key="about_page"):
        back_home()
        render_about()
