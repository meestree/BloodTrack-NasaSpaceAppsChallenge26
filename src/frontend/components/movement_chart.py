"""Movement-marked sample counts, with absent sampling periods left unknown."""
from datetime import date, datetime, timezone

import pandas as pd
import altair as alt
import streamlit as st

from frontend.components.session import require_session, show_api_error
from frontend.api import ApiError, read


def chart_data(data: dict) -> pd.DataFrame:
    hourly = data['granularity'] == 'hour'
    start = pd.Timestamp(data['from'], tz='UTC')
    end = pd.Timestamp(data['to'], tz='UTC')
    if hourly:
        end += pd.Timedelta(hours=23)
    index = pd.date_range(start, end, freq='h' if hourly else 'D')
    rows = {pd.Timestamp(row['periodo'], tz='UTC'): row['movimiento_unos'] for row in data['items']}
    return pd.DataFrame({'Movement-marked samples': [rows.get(point) for point in index]}, index=index)


def render_movement_chart(chart_container=None) -> None:
    token = require_session()
    try:
        today = datetime.now(timezone.utc).date()
        if 'reliability_dates' not in st.session_state:
            latest = read('/measurements/latest', token)
            day = date.fromisoformat(latest['date']) if latest['date'] else today
            st.session_state.reliability_dates = (day, day)
        selected = st.date_input('Measurement dates (UTC)', max_value=today, key='reliability_dates')
        if len(selected) != 2:
            st.info('Select an end date. The previous date range stays visible until selection is complete.')
            start, end = st.session_state.get('reliability_complete_dates', (today, today))
        else:
            start, end = selected
        if (end - start).days >= 3650:
            st.error('Select at most 3650 days.')
            return
        st.session_state['reliability_complete_dates'] = (start, end)
        with st.spinner('Loading movement samples…'):
            data = read('/measurements/movement', token,
                           params={'start_date': start.isoformat(), 'end_date': end.isoformat()})
        if not data['items']:
            st.info('No measurements recorded in this UTC date range.')
            if len(selected) == 2:
                return
            st.caption('Date selection preview: default values are 0; these are not recorded measurements.')
            data = {**data, 'items': [
                {'periodo': start.isoformat(), 'movimiento_unos': 0, 'muestras': 0}
            ]}
        total = sum(row['muestras'] for row in data['items'])
        moving = sum(row['movimiento_unos'] for row in data['items'])
        st.metric('Samples recorded during movement', f'{moving:,}')
        if total:
            st.caption(f'{moving / total:.1%} of {total:,} collected samples across all body regions.')
        unit = 'hour' if data['granularity'] == 'hour' else 'day'
        frame = chart_data(data).rename_axis('UTC').reset_index()
        chart = alt.Chart(frame).mark_bar(color='#b6220d').encode(
            x=alt.X('UTC:T', title=f'UTC {unit}', scale=alt.Scale(type='utc')),
            y=alt.Y('Movement-marked samples:Q', scale=alt.Scale(zero=True)),
            tooltip=['UTC:T', 'Movement-marked samples:Q'],
        ).properties(height=290)
        with chart_container if chart_container is not None else st.container():
            st.subheader(f'Movement-marked samples per {unit}')
            st.altair_chart(chart, use_container_width=True)
            st.caption('Each sample with movement = 1 counts once; these are not distinct physical movements. Periods without samples are gaps, not zero movement.')

    except ApiError as error:
        show_api_error(error)
