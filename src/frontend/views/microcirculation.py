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
                    <p>In microgravity, the redistribution of body fluids can affect blood
                    flow in different regions of the body. Monitoring microcirculation
                    helps identify potential changes in blood supply to peripheral tissues.</p>
                    <p>Our body map uses a color-coded system to display microcirculation levels:</p>
                </div>
            ''')
            render_microcirculation_legend()
            st.html('''
                <div class="temperature-copy temperature-copy--closing">
                    <p>This visualization helps identify potential circulatory changes
                    that may require further monitoring.</p>
                </div>
            ''')
        with body_map:
            render_body_map(metric='caudal')
