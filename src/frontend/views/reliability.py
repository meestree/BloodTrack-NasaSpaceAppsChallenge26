"""Measurement reliability explanation and movement sample chart."""
import streamlit as st

from frontend.components.movement_chart import render_movement_chart


def render_reliability() -> None:
    st.html('<h1 class="temperature-title reliability-title">Mesurement reliability</h1>')
    with st.container(key='temperature-content'):
        explanation, chart = st.columns([1.7, 1], gap='large')
        with explanation:
            st.html('''
                <div class="temperature-copy">
                    <p>Astronaut movement can affect sensor contact with the skin and
                    cause signal interference, especially in microcirculation measurements,
                    reducing the accuracy of the results.</p>
                    <p>Our application tracks movement intensity over time and displays
                    it through a graph, allowing periods of increased activity to be identified.</p>
                    <p>By comparing this data with physiological measurements, we can
                    identify when results may be distorted, preventing measurement errors
                    from being mistaken for actual physiological changes.</p>
                </div>
            ''')
        with chart:
            render_movement_chart()
