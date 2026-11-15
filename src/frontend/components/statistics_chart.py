"""Per-region hourly/daily means and sample standard deviations from the API."""
from datetime import date, datetime, timezone
from math import sqrt

import altair as alt
import pandas as pd
import streamlit as st

from frontend.components.session import require_session, show_api_error
from frontend.api import ApiError, read, clear_data_cache, begin_run
from frontend.components.flow import flow_ranges

GROUPS = {'Neck / head': ('Neck',), 'Arms': ('Left arm', 'Right arm'),
          'Legs': ('Left leg', 'Right leg')}


def thresholds(metric: str, parts: tuple) -> tuple[tuple, tuple]:
    if metric == 'temperatura':
        return (35.5, 37), (34.5, 39)
    danger_low, normal_low, normal_high, danger_high = flow_ranges(parts[0])
    return (normal_low, normal_high), (danger_low, danger_high)


def chart_rows(data: dict, parts: tuple) -> list[dict]:
    hourly = data['granularity'] == 'hour'
    end = pd.Timestamp(data['to'], tz='UTC') + (pd.Timedelta(hours=23) if hourly else pd.Timedelta(0))
    periods = pd.date_range(pd.Timestamp(data['from'], tz='UTC'), end, freq='h' if hourly else 'D')
    lookup = {(row['nombre'], pd.Timestamp(row['periodo'], tz='UTC')): row for row in data['items']}
    result = []
    region = next((name for name, group in GROUPS.items() if group == parts), parts[0])
    for point in periods:
        rows = [lookup[(part, point)] for part in parts if (part, point) in lookup]
        samples = sum(row['muestras'] for row in rows) if rows else None
        mean = (sum(row['media'] * row['muestras'] for row in rows) / samples
                if samples else (0 if rows else None))
        sd = None
        if samples and samples > 1 and all(
                row['muestras'] <= 1 or row['desviacion_estandar'] is not None for row in rows):
            # Pool within-region variance and between-region mean differences.
            m2 = sum((row['muestras'] - 1) * (row['desviacion_estandar'] or 0) ** 2
                     + row['muestras'] * (row['media'] - mean) ** 2 for row in rows)
            sd = sqrt(max(0, m2) / (samples - 1))
        result.append({'UTC': point.isoformat(), 'Region': region, 'Mean': mean,
            'SD': sd, 'Samples': samples,
            'Lower': mean - sd if sd is not None else None,
            'Upper': mean + sd if sd is not None else None})
    return result


def make_chart(data: dict, parts: tuple, metric: str):
    unit = 'Temperature (API value)' if metric == 'temperatura' else 'Microcirculation (PU)'
    frame = alt.Data(values=chart_rows(data, parts))
    base = alt.Chart(frame).encode(
        x=alt.X('UTC:T', title='UTC hour' if data['granularity'] == 'hour' else 'UTC date', scale=alt.Scale(type='utc')),
        color=alt.Color('Region:N', title='Body region'))
    line = base.mark_line(point=True, invalid='break-paths-show-domains').encode(
        y=alt.Y('Mean:Q', title=unit, scale=alt.Scale(zero=False)),
        tooltip=['UTC:T', 'Region:N', 'Mean:Q', 'SD:Q', 'Samples:Q'])
    band = base.mark_area(opacity=.15, invalid='break-paths-show-domains').encode(y='Lower:Q', y2='Upper:Q')
    caution, danger = thresholds(metric, parts)
    def rules(values, label, color):
        return alt.Chart(alt.Data(values=[{'Threshold': value, 'Level': label} for value in values])).mark_rule(
            color=color, strokeDash=[6, 4]).encode(y='Threshold:Q', tooltip=['Level:N', 'Threshold:Q'])
    return (band + line + rules(caution, 'Caution', '#f5cf36')
            + rules(danger, 'Danger', '#e44838')).properties(height=290)


@st.fragment
def render_statistics_chart(metric: str) -> None:
    begin_run()
    token = require_session()
    st.divider()
    try:
        today = datetime.now(timezone.utc).date()
        if 'analysis_dates' not in st.session_state:
            latest = read('/measurements/latest', token)
            day = date.fromisoformat(latest['date']) if latest['date'] else today
            st.session_state.analysis_dates = (day, day)
        selected = st.date_input('Analysis dates (UTC)', max_value=today, key='analysis_dates')
        if len(selected) != 2:
            st.info('Select an end date. The previous date range stays visible until selection is complete.')
            start, end = st.session_state.get('analysis_complete_dates', (today, today))
        else:
            start, end = selected
        if (end - start).days >= 3650:
            st.error('Select at most 3650 days.')
            return
        st.session_state['analysis_complete_dates'] = (start, end)
        with st.spinner('Loading statistical analysis…'):
            data = read('/measurements/statistics', token,
                params={'start_date': start.isoformat(), 'end_date': end.isoformat(), 'metric': metric})
        if not data['items']:
            st.info('No measurements recorded in this UTC date range.')
            if len(selected) == 2:
                return
            st.caption('Date selection preview: default values are 0; these are not recorded measurements.')
            data = {**data, 'items': [
                {'nombre': part, 'periodo': start.isoformat(), 'media': 0,
                 'desviacion_estandar': None, 'muestras': 0}
                for parts in GROUPS.values() for part in parts
            ]}
        for name, parts in GROUPS.items():
            st.subheader(name)
            if not any(row['nombre'] in parts for row in data['items']):
                st.info('No measurements for this body region in the selected range.')
                continue
            st.altair_chart(make_chart(data, parts, metric), use_container_width=True)
        st.button('Refresh analysis', on_click=clear_data_cache)
    except ApiError as error:
        show_api_error(error)
        st.button('Retry analysis', on_click=clear_data_cache)
