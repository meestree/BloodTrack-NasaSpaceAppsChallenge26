"""Measurement reliability explanation and movement sample chart."""
import streamlit as st

from frontend.components.movement_chart import render_movement_chart


def render_reliability() -> None:
    st.html('<h1 class="temperature-title reliability-title">Measurement reliability</h1>')
    with st.container(key='temperature-content'):
        explanation, chart = st.columns([1.7, 1], gap='large')
        with explanation:
            st.html('''
                <div class="temperature-copy">
                    <p>By comparing this data with physiological measurements, we can
                    identify when results may be distorted, preventing measurement errors
                    from being mistaken for actual physiological changes.</p>
                </div>
            ''')
            render_movement_chart(chart_container=chart)
