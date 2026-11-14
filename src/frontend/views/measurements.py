"""Profile, collection, history, and summaries backed only by the authenticated API."""
from datetime import datetime, timezone
import math

import pandas as pd
import streamlit as st

from frontend.api import ApiError, request


def body_parts(token: str) -> dict[int, str]:
    with st.spinner('Loading body regions…'):
        return {row['id_parte']: row['nombre'] for row in request('GET', '/body-parts', token)}


def render_profile(user: dict) -> None:
    st.title('My profile')
    for label, field in (('Username', 'nombre_usuario'), ('Email', 'email'),
                         ('Date of birth', 'fecha_nacimiento'), ('Age', 'edad'),
                         ('Account created', 'creado_en')):
        st.text(f'{label}: {user[field]}')
    st.caption('Profile information comes from your current authenticated account.')


def render_collection(token: str) -> None:
    st.title('Record a measurement')
    parts = body_parts(token)
    if not parts:
        st.info('No body regions are configured. Contact your administrator before recording measurements.')
        return
    st.caption('Enter sensor values as supplied by your device. The API does not specify sensor units.')
    with st.form('measure_form', clear_on_submit=False):
        part = st.selectbox('Body region', list(parts), format_func=parts.get, key='measure_part')
        errors = {'id_parte': st.empty()}
        now = st.checkbox('Use current UTC time', value=True, key='measure_now')
        timestamp = st.text_input('Timestamp with timezone', placeholder='2020-01-02T12:00:00+00:00',
                                  help='Used when current UTC time is unchecked.', key='measure_timestamp')
        errors['timestamp'] = st.empty()
        temperature = st.number_input('Temperature (temperatura)', value=None, format='%0.4f', key='measure_temperature')
        errors['temperatura'] = st.empty()
        flow = st.number_input('Microcirculation (caudal)', value=None, format='%0.4f', key='measure_flow')
        errors['caudal'] = st.empty()
        movement = st.selectbox('Movement (movimiento)', [0, 1], index=None,
                                format_func=lambda value: '1 — Movement detected' if value else '0 — No movement detected',
                                key='measure_movement')
        errors['movimiento'] = st.empty()
        submitted = st.form_submit_button('Save measurement')
    if not submitted:
        return
    fields = {}
    recorded = datetime.now(timezone.utc)
    if not now:
        try:
            recorded = datetime.fromisoformat(timestamp)
            if recorded.tzinfo is None or recorded.utcoffset() is None:
                raise ValueError
            if recorded > datetime.now(timezone.utc):
                fields['timestamp'] = 'The measurement cannot be in the future.'
        except ValueError:
            fields['timestamp'] = 'Enter an ISO timestamp including a timezone.'
    for name, value in (('temperatura', temperature), ('caudal', flow)):
        if value is None or not math.isfinite(value):
            fields[name] = 'Enter a finite sensor value.'
    if movement is None:
        fields['movimiento'] = 'Select whether movement was detected.'
    if not fields:
        try:
            with st.spinner('Saving measurement…'):
                result = request('POST', '/measurements', token, json={'measurements': [{
                    'id_parte': part, 'timestamp': recorded.astimezone(timezone.utc).isoformat(),
                    'temperatura': temperature, 'caudal': flow, 'movimiento': movement,
                }]})
            for key in ('map_date_initialized', 'reliability_dates', 'analysis_dates'):
                st.session_state.pop(key, None)
            st.success(f"Saved {result['created']} measurement. Open history or summaries to view it.")
        except ApiError as error:
            if error.status != 422:
                raise
            st.error(str(error))
            fields = error.fields
    for name, message in fields.items():
        if name in errors:
            errors[name].error(message)


def reset_history() -> None:
    st.session_state['history_offset'] = 0


def filters(token: str, key: str) -> tuple[dict, dict]:
    parts = body_parts(token)
    callback = reset_history if key == 'history' else None
    days = st.number_input('UTC calendar days, including today', min_value=1, max_value=3650,
                           value=7, step=1, key=f'{key}_days', on_change=callback)
    part = st.selectbox('Body region', [None, *parts],
                        format_func=lambda value: 'All regions' if value is None else parts[value],
                        key=f'{key}_part', on_change=callback)
    params = {'days': int(days)}
    if part is not None:
        params['id_parte'] = part
    st.caption('Today means today so far in UTC. Regions and dates without samples remain missing.')
    return params, parts


def show_table(data: dict, parts: dict) -> None:
    st.caption(f"UTC window: {data['from']} → {data['to']}")
    if not data['items']:
        st.info('No measurements in this UTC window for the selected regions.')
        return
    frame = pd.DataFrame(data['items'])
    frame.insert(0, 'Body region', frame['id_parte'].map(parts))
    st.dataframe(frame, hide_index=True, use_container_width=True)


def change_offset(value: int) -> None:
    st.session_state['history_offset'] = value


def render_history(token: str) -> None:
    st.title('Measurement history')
    params, parts = filters(token, 'history')
    limit = st.selectbox('Rows per page', [25, 100, 1000], key='history_limit', on_change=reset_history)
    offset = st.session_state.setdefault('history_offset', 0)
    with st.spinner('Loading measurement history…'):
        data = request('GET', '/measurements', token, params={**params, 'limit': limit, 'offset': offset})
    # Recover gracefully if records were removed while viewing a later page.
    if offset and offset >= data['total']:
        reset_history()
        st.rerun()
    st.caption(f"{data['total']} measurements · newest first")
    show_table(data, parts)
    previous, following = st.columns(2)
    previous.button('Previous', disabled=offset == 0, on_click=change_offset,
                    args=(max(0, offset - limit),), key='history_previous')
    following.button('Next', disabled=offset + limit >= data['total'], on_click=change_offset,
                     args=(offset + limit,), key='history_next')
    st.button('Refresh history')


def render_daily(token: str) -> None:
    st.title('Daily summaries')
    params, parts = filters(token, 'daily')
    with st.spinner('Loading daily summaries…'):
        data = request('GET', '/measurements/daily', token, params=params)
    show_table(data, parts)
    st.caption('Daily means and movement-marked sample counts, grouped by region and UTC date.')
    st.button('Refresh daily summaries')


def render_analytics(token: str) -> None:
    st.title('Period analytics')
    params, parts = filters(token, 'period')
    with st.spinner('Loading period analytics…'):
        data = request('GET', '/measurements/analytics', token, params=params)
    show_table(data, parts)
    st.caption('Means are weighted by samples. Coverage is the fraction of UTC days with data; missing days are not zero readings.')
    st.button('Refresh period analytics')
