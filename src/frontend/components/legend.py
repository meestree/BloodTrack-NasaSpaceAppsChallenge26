"""Text labels keep the legend understandable without color perception."""

import streamlit as st
from frontend.components.flow import FLOW_RANGES


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
    rows = ''.join(
        f'<tr><th scope="row">{zone}</th><td>&lt; {low} PU</td>'
        f'<td>{low}–{normal_low} PU</td><td>{normal_low}–{normal_high} PU</td>'
        f'<td>{normal_high}–{high} PU</td><td>&gt; {high} PU</td></tr>'
        for zone, (low, normal_low, normal_high, high) in FLOW_RANGES.items()
    )
    st.html(
        '<div class="flow-ranges"><table aria-label="Microcirculation thresholds in PU">'
        '<thead><tr><th>Region</th><th>Low danger</th><th>Low warning</th>'
        '<th>Normal</th><th>High warning</th><th>High danger</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )
