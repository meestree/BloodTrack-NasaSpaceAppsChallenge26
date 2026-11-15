"""Statistical analysis landing page and metric charts."""
import streamlit as st

from frontend.components.statistics_chart import render_statistics_chart


def render_statistical_analysis() -> None:
    selected_metric = st.session_state.get('analysis_metric')
    st.html('<h1 class="temperature-title statistical-title">Statistical Analysis</h1>')
    with st.container(key='temperature-content'):
        with st.container(key='analysis-actions'):
            temperature, microcirculation = st.columns(2, gap='small')
            with temperature:
                st.button('Temperature', key='analysis-temperature',
                          type='primary' if selected_metric == 'temperatura' else 'secondary',
                          use_container_width=True, on_click=select_metric, args=("temperatura",),
                          help='Show temperature statistics.')
            with microcirculation:
                st.button('Microcirculation', key='analysis-microcirculation',
                          type='primary' if selected_metric == 'caudal' else 'secondary',
                          use_container_width=True, on_click=select_metric, args=("caudal",),
                          help='Show microcirculation statistics.')

    if st.session_state.get('analysis_metric'):
        render_statistics_chart(st.session_state.analysis_metric)


def select_metric(metric: str) -> None:
    st.session_state.analysis_metric = metric
