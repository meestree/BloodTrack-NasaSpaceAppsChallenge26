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
                    <p>In microgravity, changes in blood circulation can affect skin
                    temperature. Monitoring different body regions helps identify
                    unusual variations that may indicate changes in peripheral blood flow.</p>
                    <p>Our body map uses a color-coded system to display temperature levels:</p>
                </div>
            """)
            render_temperature_legend()
            st.html("""
                <div class="temperature-copy temperature-copy--closing">
                    <p>This visualization helps detect temperature changes that may
                    require further monitoring.</p>
                </div>
            """)
        with body_map:
            render_body_map()
