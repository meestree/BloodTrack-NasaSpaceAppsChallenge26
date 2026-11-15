"""Compact body-map legends with text labels alongside each color."""

import streamlit as st


def _render_legend(label: str) -> None:
    st.html(f"""
        <ul class="temperature-legend" aria-label="{label} color legend">
            <li><span class="legend-dot legend-dot--normal" aria-hidden="true"></span>
                <span>Green = fine</span></li>
            <li><span class="legend-dot legend-dot--caution" aria-hidden="true"></span>
                <span>Yellow = caution</span></li>
            <li><span class="legend-dot legend-dot--danger" aria-hidden="true"></span>
                <span>Red = danger</span></li>
        </ul>
    """)


def render_temperature_legend() -> None:
    _render_legend('Temperature')


def render_microcirculation_legend() -> None:
    _render_legend('Microcirculation')
