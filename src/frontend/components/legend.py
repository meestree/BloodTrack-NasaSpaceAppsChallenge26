"""Text labels keep the legend understandable without color perception."""

import streamlit as st


def render_temperature_legend() -> None:
    st.html("""
        <ul class="temperature-legend" aria-label="Temperature color legend">
            <li><span class="legend-dot legend-dot--normal" aria-hidden="true"></span>
                <span>Green: Within the normal range.</span></li>
            <li><span class="legend-dot legend-dot--caution" aria-hidden="true"></span>
                <span>Yellow: Moderate deviation from normal values.</span></li>
            <li><span class="legend-dot legend-dot--danger" aria-hidden="true"></span>
                <span>Red: Significant deviation from normal values.</span></li>
        </ul>
    """)


def render_microcirculation_legend() -> None:
    st.html('''
        <ul class="temperature-legend" aria-label="Microcirculation color legend">
            <li><span class="legend-dot legend-dot--normal" aria-hidden="true"></span>
                <span>Green — Normal: Within the expected reference range.</span></li>
            <li><span class="legend-dot legend-dot--caution" aria-hidden="true"></span>
                <span>Yellow — Warning: Moderate deviation from normal values.</span></li>
            <li><span class="legend-dot legend-dot--danger" aria-hidden="true"></span>
                <span>Red — Alert: Significant deviation from normal values.</span></li>
        </ul>
    ''')
