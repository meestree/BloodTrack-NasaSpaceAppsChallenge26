"""Shared page configuration, styles, and sidebar navigation."""

from pathlib import Path

import streamlit as st


STYLESHEET = Path(__file__).resolve().parents[1] / "assets" / "styles.css"


def configure_page() -> None:
    st.set_page_config(
        page_title="Temperature | Body monitoring",
        page_icon="🌡️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.html(f"<style>{STYLESHEET.read_text(encoding='utf-8')}</style>")


def render_sidebar(temperature_page: st.Page, microcirculation_page: st.Page, reliability_page: st.Page, analysis_page: st.Page) -> None:
    with st.sidebar:
        st.title("Body monitoring")
        st.page_link(temperature_page, label="Temperature", icon=":material/device_thermostat:")

        st.page_link(microcirculation_page, label="Microcirculation", icon=":material/water_drop:")

        st.page_link(reliability_page, label="Measurement reliability", icon=":material/monitoring:")

        st.page_link(analysis_page, label="Statistical Analysis", icon=":material/analytics:")
