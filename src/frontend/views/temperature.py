"""Temperature explanation page based on the supplied design reference."""

import streamlit as st

from frontend.components.body_map import render_body_map
from frontend.components.legend import render_temperature_legend


def render_temperature() -> None:
    st.html('<h1 class="temperature-title">Temperature</h1>')

    with st.container(key="temperature-content"):
        explanation, body_map = st.columns([1.7, 1], gap="large")
        with explanation:
            st.html("""
                <div class="temperature-copy">
                    <p>Our body map uses a color-coded system to display temperature levels:</p>
                </div>
            """)
            readings_table = st.container()

        with body_map:
            render_body_map(readings_container=readings_table)
        with explanation:
            render_temperature_legend()
