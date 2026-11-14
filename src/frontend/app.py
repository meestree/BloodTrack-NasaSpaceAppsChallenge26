"""Run from the repository root: streamlit run src/frontend/app.py."""

import streamlit as st

from frontend.components.layout import configure_page, render_sidebar
from frontend.views.temperature import render_temperature
from frontend.views.reliability import render_reliability
from frontend.views.statistical_analysis import render_statistical_analysis
from frontend.views.microcirculation import render_microcirculation


def main() -> None:
    configure_page()
    temperature = st.Page(render_temperature, title="Temperature", default=True)
    microcirculation = st.Page(render_microcirculation, title="Microcirculation", url_path="microcirculation")
    reliability = st.Page(render_reliability, title="Measurement reliability", url_path="reliability")
    analysis = st.Page(render_statistical_analysis, title="Statistical Analysis", url_path="statistical-analysis")
    navigation = st.navigation([temperature, microcirculation, reliability, analysis], position="hidden")
    render_sidebar(temperature, microcirculation, reliability, analysis)
    navigation.run()


if __name__ == "__main__":
    main()
