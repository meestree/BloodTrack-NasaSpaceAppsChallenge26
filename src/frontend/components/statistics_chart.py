"""Per-region hourly/daily means and sample standard deviations from the API."""
from datetime import date, datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from frontend.components.session import clear_session, require_session
from frontend.services.api import ApiError, request

GROUPS = {'Neck / head': ('Cuello',), 'Arms': ('Brazo izquierdo', 'Brazo derecho'),
          'Legs': ('Pierna izquierda', 'Pierna derecha')}


def chart_rows(data: dict, parts: tuple) -> list[dict]:
    hourly = data['granularity'] == 'hour'
    end = pd.Timestamp(data['to'], tz='UTC') + (pd.Timedelta(hours=23) if hourly else pd.Timedelta(0))
    periods = pd.date_range(pd.Timestamp(data['from'], tz='UTC'), end, freq='h' if hourly else 'D')
    lookup = {(row['nombre'], pd.Timestamp(row['periodo'], tz='UTC')): row for row in data['items']}
    result = []
    for part in parts:
        for point in periods:
            row = lookup.get((part, point))
            mean = row['media'] if row else None
            sd = row['desviacion_estandar'] if row else None
            result.append({'UTC': point.isoformat(), 'Region': part, 'Mean': mean,
                'SD': sd, 'Samples': row['muestras'] if row else None,
                'Lower': mean - sd if sd is not None else None,
                'Upper': mean + sd if sd is not None else None})
    return result


def make_chart(data: dict, parts: tuple, metric: str):
    unit = '°C' if metric == 'temperatura' else 'ml/min'
    frame = alt.Data(values=chart_rows(data, parts))
    base = alt.Chart(frame).encode(
        x=alt.X('UTC:T', title='UTC hour' if data['granularity'] == 'hour' else 'UTC date', scale=alt.Scale(type='utc')),
        color=alt.Color('Region:N', title='Body region'))
    line = base.mark_line(point=True, invalid='break-paths-show-domains').encode(
        y=alt.Y('Mean:Q', title=unit, scale=alt.Scale(zero=False)),
        tooltip=['UTC:T', 'Region:N', 'Mean:Q', 'SD:Q', 'Samples:Q'])
    band = base.mark_area(opacity=.15, invalid='break-paths-show-domains').encode(y='Lower:Q', y2='Upper:Q')
    limits = [35.5, 37] if metric == 'temperatura' else ([750] if parts == ('Cuello',) else [750, 1000])
    reference = alt.Chart(alt.Data(values=[{'Reference': value} for value in limits])).mark_rule(
        color='#00ed10', strokeDash=[6, 4]).encode(y='Reference:Q', tooltip=['Reference:Q'])
    return (band + line + reference).properties(height=290).interactive()


def render_statistics_chart(metric: str) -> None:
    token = require_session()
    label = 'Temperature' if metric == 'temperatura' else 'Microcirculation'
    st.divider()
    st.subheader(f'{label} — Statistical Analysis')
    try:
        today = datetime.now(timezone.utc).date()
        if 'analysis_dates' not in st.session_state:
            latest = request('GET', '/measurements/latest', token)
            day = date.fromisoformat(latest['date']) if latest['date'] else today
            st.session_state.analysis_dates = (day, day)
        selected = st.date_input('Analysis dates (UTC)', max_value=today, key='analysis_dates')
        if len(selected) != 2:
            st.info('Select an end date, or select the same date twice for hourly detail.')
            return
        start, end = selected
        if (end - start).days >= 3650:
            st.error('Select at most 3650 days.')
            return
        with st.spinner('Loading statistical analysis…'):
            data = request('GET', '/measurements/statistics', token,
                params={'start_date': start.isoformat(), 'end_date': end.isoformat(), 'metric': metric})
        if not data['items']:
            st.info('No measurements recorded in this UTC date range.')
            return
        period = 'hour' if data['granularity'] == 'hour' else 'day'
        st.caption(f'Mean per UTC {period}. Shading shows ±1 sample standard deviation; it requires at least two samples. Missing periods remain gaps. Left and right limbs are separate series.')
        for name, parts in GROUPS.items():
            st.subheader(name)
            if not any(row['nombre'] in parts for row in data['items']):
                st.info('No measurements for this body region in the selected range.')
                continue
            st.altair_chart(make_chart(data, parts, metric), use_container_width=True)
            reference = '35.5–37 °C' if metric == 'temperatura' else ('approximately 750 ml/min' if name == 'Neck / head' else '750–1,000 ml/min')
            st.caption(f'Green dashed reference: {reference}.')
        with st.expander('Statistics by period'):
            st.dataframe(pd.DataFrame(data['items']).rename(columns={
                'nombre': 'Body region', 'periodo': 'UTC period', 'muestras': 'Samples',
                'media': 'Mean', 'desviacion_estandar': 'Sample SD',
                'minimo': 'Minimum', 'maximo': 'Maximum'}), hide_index=True)
        if st.button('Refresh analysis'):
            st.rerun()
        if st.button('Sign out', key='analysis-logout'):
            request('POST', '/auth/logout', token)
            clear_session()
            st.rerun()
    except ApiError as error:
        if error.status == 401:
            clear_session()
            st.rerun()
        st.error(str(error))
        if st.button('Retry analysis'):
            st.rerun()
