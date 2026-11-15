"""Microcirculation page using the shared API-backed body map."""
import streamlit as st

from frontend.components.body_map import render_body_map
from frontend.components.legend import render_microcirculation_legend


def render_microcirculation() -> None:
    st.html('<h1 class="temperature-title">Microcirculation</h1>')
    with st.container(key='temperature-content'):
        explanation, body_map = st.columns([1.7, 1], gap='large')
        with explanation:
            st.html('''
                <div class="temperature-copy">
                    <p>Our body map uses a color-coded system to display microcirculation levels:</p>
                </div>
            ''')
            render_microcirculation_legend()
            readings_table = st.container()
        with body_map:
            render_body_map(metric='caudal', readings_container=readings_table)
