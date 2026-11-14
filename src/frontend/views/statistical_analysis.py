"""Statistical analysis landing page and metric charts."""
import streamlit as st

from frontend.components.statistics_chart import render_statistics_chart


def render_statistical_analysis() -> None:
    st.html('<h1 class="temperature-title statistical-title">Statistical Analysis</h1>')
    with st.container(key='temperature-content'):
        explanation, actions = st.columns([1.7, 1], gap='large')
        with explanation:
            st.html('''
                <div class="temperature-copy">
                    <p>Our application tracks temperature and microcirculation over time,
                    displaying separate graphs for the head, arms, and legs to identify
                    changes in each body region.</p>
                    <p>Each graph includes statistical averages, standard deviations,
                    and reference limits, allowing measurements to be compared with
                    expected normal values.</p>
                    <p>This analysis helps identify trends, detect unusual variations,
                    and monitor physiological changes that may occur during prolonged
                    exposure to microgravity.</p>
                </div>
            ''')
        with actions:
            with st.container(key='analysis-actions'):
                st.button('Temperature', key='analysis-temperature', type='primary',
                          use_container_width=True, on_click=select_metric, args=("temperatura",),
                          help='Show temperature statistics.')
                st.button('Microcirculation', key='analysis-microcirculation', type='primary',
                          use_container_width=True, on_click=select_metric, args=("caudal",),
                          help='Show microcirculation statistics.')

    if st.session_state.get('analysis_metric'):
        render_statistics_chart(st.session_state.analysis_metric)


def select_metric(metric: str) -> None:
    st.session_state.analysis_metric = metric
