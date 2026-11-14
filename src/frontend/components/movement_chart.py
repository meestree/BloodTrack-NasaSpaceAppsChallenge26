"""Movement-marked sample counts, with absent sampling periods left unknown."""
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from frontend.components.session import clear_session, require_session
from frontend.services.api import ApiError, request


def chart_data(data: dict) -> pd.DataFrame:
    hourly = data['granularity'] == 'hour'
    start = pd.Timestamp(data['from'], tz='UTC')
    end = pd.Timestamp(data['to'], tz='UTC')
    if hourly:
        end += pd.Timedelta(hours=23)
    index = pd.date_range(start, end, freq='h' if hourly else 'D')
    rows = {pd.Timestamp(row['periodo'], tz='UTC'): row['movimiento_unos'] for row in data['items']}
    return pd.DataFrame({'Movement-marked samples': [rows.get(point) for point in index]}, index=index)


def render_movement_chart() -> None:
    token = require_session()
    try:
        today = datetime.now(timezone.utc).date()
        if 'reliability_dates' not in st.session_state:
            latest = request('GET', '/measurements/latest', token)
            day = date.fromisoformat(latest['date']) if latest['date'] else today
            st.session_state.reliability_dates = (day, day)
        selected = st.date_input('Measurement dates (UTC)', max_value=today, key='reliability_dates')
        if len(selected) != 2:
            st.info('Select an end date, or select the same date twice for hourly detail.')
            return
        start, end = selected
        if (end - start).days >= 3650:
            st.error('Select at most 3650 days.')
            return
        with st.spinner('Loading movement samples…'):
            data = request('GET', '/measurements/movement', token,
                           params={'start_date': start.isoformat(), 'end_date': end.isoformat()})
        if not data['items']:
            st.info('No measurements recorded in this UTC date range.')
            return
        total = sum(row['muestras'] for row in data['items'])
        moving = sum(row['movimiento_unos'] for row in data['items'])
        st.metric('Samples recorded during movement', f'{moving:,}')
        st.caption(f'{moving / total:.1%} of {total:,} collected samples across all body regions.')
        unit = 'hour' if data['granularity'] == 'hour' else 'day'
        st.subheader(f'Movement-marked samples per {unit}')
        st.bar_chart(chart_data(data), color='#b6220d')
        st.caption('UTC time. Each sample with movimiento = 1 counts once; these are not distinct physical movements. Periods without samples are gaps, not zero movement.')
        with st.expander('Recorded sample counts'):
            st.dataframe(pd.DataFrame(data['items']).rename(columns={
                'periodo': 'UTC period', 'muestras': 'Collected samples',
                'movimiento_unos': 'Movement-marked samples'}), hide_index=True)
        if st.button('Refresh movement data'):
            st.rerun()
        if st.button('Sign out', key='reliability_logout'):
            request('POST', '/auth/logout', token)
            clear_session()
            st.rerun()
    except ApiError as error:
        if error.status == 401:
            clear_session()
            st.rerun()
        st.error(str(error))
        if st.button('Retry movement data'):
            st.rerun()
