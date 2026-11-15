"""Daily summaries backed only by the authenticated API."""
import pandas as pd
import streamlit as st

from frontend.api import read, clear_data_cache


def body_parts(token: str) -> dict[int, str]:
    with st.spinner('Loading body regions…'):
        return {row['id_parte']: row['nombre'] for row in read('/body-parts', token)}


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
    for part_id, rows in frame.groupby('id_parte', sort=True):
        st.subheader(parts.get(part_id, f'Body region {part_id}'), anchor=False)
        table = rows[['fecha', 'muestras', 'temperatura_media', 'caudal_media', 'movimiento_unos']].rename(columns={
            'fecha': 'Date', 'muestras': 'Samples',
            'temperatura_media': 'Average temperature', 'caudal_media': 'Average flow rate (PU)',
            'movimiento_unos': 'Movements registered',
        })
        st.table(table.style.hide(axis='index').format({
            'Samples': '{:,.0f}', 'Average temperature': '{:,.2f}',
            'Average flow rate (PU)': '{:,.2f}', 'Movements registered': '{:,.0f}',
        }))


def render_daily(token: str) -> None:
    st.title('Daily summaries')
    params, parts = filters(token, 'daily')
    with st.spinner('Loading daily summaries…'):
        data = read('/measurements/daily', token, params=params)
    show_table(data, parts)
    st.caption('Daily means and movement-marked sample counts, grouped by region and UTC date.')
    st.button('Refresh daily summaries', on_click=clear_data_cache)
