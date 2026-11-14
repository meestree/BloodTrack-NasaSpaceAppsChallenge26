"""Daily summaries backed only by the authenticated API."""
import pandas as pd
import streamlit as st

from frontend.api import request


def body_parts(token: str) -> dict[int, str]:
    with st.spinner('Loading body regions…'):
        return {row['id_parte']: row['nombre'] for row in request('GET', '/body-parts', token)}


def filters(token: str, key: str) -> tuple[dict, dict]:
    parts = body_parts(token)
    days = st.number_input('UTC calendar days, including today', min_value=1, max_value=3650,
                           value=7, step=1, key=f'{key}_days')
    part = st.selectbox('Body region', [None, *parts],
                        format_func=lambda value: 'All regions' if value is None else parts[value],
                        key=f'{key}_part')
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


def render_daily(token: str) -> None:
    st.title('Daily summaries')
    params, parts = filters(token, 'daily')
    with st.spinner('Loading daily summaries…'):
        data = request('GET', '/measurements/daily', token, params=params)
    show_table(data, parts)
    st.caption('Daily means and movement-marked sample counts, grouped by region and UTC date.')
    st.button('Refresh daily summaries')
