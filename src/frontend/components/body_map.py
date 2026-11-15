"""Body maps driven exclusively by authenticated API measurements."""
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st
import pandas as pd

from frontend.components.session import require_session, show_api_error
from frontend.api import ApiError
from frontend import api
from frontend.components.assets import image_data_url
from frontend.components.flow import flow_ranges

RESOURCES = Path(__file__).resolve().parents[2] / 'resources'
PARTS = ('Neck', 'Left arm', 'Right arm', 'Left leg', 'Right leg')


def temperature_color(value: float) -> str:
    if value < 34.5 or value > 39:
        return 'R'
    if 35.5 <= value <= 37:
        return 'G'
    # Includes 34.5 and the unspecified 38.9–39 gap as caution.
    return 'Y'


def caudal_color(value: float, part: str) -> str:
    danger_low, normal_low, normal_high, danger_high = flow_ranges(part)
    if value < danger_low or value > danger_high:
        return 'R'
    return 'G' if normal_low <= value <= normal_high else 'Y'


def reading_color(row: dict, part: str, metric: str) -> str:
    return caudal_color(row['caudal'], part) if metric == 'caudal' else temperature_color(row['temperatura'])


def map_filename(readings: dict, metric: str = 'temperatura') -> str | None:
    if any(part not in readings for part in PARTS):
        return None
    colors = [reading_color(readings[part], part, metric) for part in PARTS]
    severity = {'G': 0, 'Y': 1, 'R': 2}
    arms = max(colors[1:3], key=severity.get)
    legs = max(colors[3:5], key=severity.get)
    return f'H{colors[0]}_A{arms}_L{legs}.png'


def reset_map_date() -> None:
    st.session_state.pop('map_date_initialized', None)
    api.clear_data_cache()


def render_movement_summary(selected: date, token: str) -> None:
    """Show movement totals for every sample on the map's selected UTC date."""
    try:
        data = api.read('/measurements/movement', token, params={
            'start_date': selected.isoformat(), 'end_date': selected.isoformat(),
        })
    except ApiError as error:
        show_api_error(error)
        st.button('Retry movement summary', on_click=api.clear_data_cache)
        return
    total = sum(row['muestras'] for row in data['items'])
    if not total:
        st.info('No samples available for the movement summary on this UTC date.')
        return
    moving = sum(row['movimiento_unos'] for row in data['items'])
    st.metric('Samples recorded during movement', f'{moving:,}')
    st.caption(f'{moving / total:.1%} of {total:,} collected samples across all body regions.')


def render_body_map(metric: str = 'temperatura', readings_container=None) -> None:
    label = 'Microcirculation (PU)' if metric == 'caudal' else 'Temperature'
    token = require_session()
    try:
        with st.spinner(f'Loading {label.lower()} measurements…'):
            latest = None
            if not st.session_state.get('map_date_initialized'):
                latest = api.read('/measurements/latest', token)
                st.session_state.map_date = date.fromisoformat(latest['date']) if latest['date'] else datetime.now(timezone.utc).date()
                st.session_state.map_date_initialized = True
            st.button('Latest readings', on_click=reset_map_date)
            selected = st.date_input('Measurement date (UTC)', max_value=datetime.now(timezone.utc).date(), key='map_date')
            data = (latest if latest is not None else
                    api.read('/measurements/latest', token, params={'date': selected.isoformat()}))
        readings = {row['nombre']: row for row in data['items']}
        if not readings:
            with readings_container if readings_container is not None else st.container():
                st.info('No measurements recorded on this UTC date.')
            return
        filename = map_filename(readings, metric)
        if filename:
            image = RESOURCES / filename
            if image.is_file():
                st.html(f'<div class="body-map-frame"><img class="body-map-image" src="{image_data_url(image)}" alt="{label} map: neck, arms and legs. Individual readings and statuses are listed below."></div>')
            else:
                st.error('The body map image is unavailable.')
        else:
            st.warning('Some regions have no measurements for this date. The map is unavailable until all five regions have readings.')
        status = {'G': 'Normal', 'Y': 'Warning', 'R': 'Alert'} if metric == 'caudal' else {'G': 'Normal', 'Y': 'Caution', 'R': 'Danger'}
        rows = []
        for part in dict.fromkeys((*PARTS, *readings)):
            row = readings.get(part)
            rows.append({
                'Body region': part,
                label: row[metric] if row else None,
                **({'Flow rate (PU)': row['caudal'] if row else None} if metric != 'caudal' else {}),
                'Movement': ('Yes' if row['movimiento'] else 'No') if row else None,
                'Status': status[reading_color(row, part, metric)] if row else 'No measurement',
            })
        with readings_container if readings_container is not None else st.container():
            formats = {label: '{:.2f}'}
            if metric != 'caudal':
                formats['Flow rate (PU)'] = '{:.2f}'
            st.table(pd.DataFrame(rows).style.hide(axis='index').format(formats, na_rep='—'))
            render_movement_summary(selected, token)
    except ApiError as error:
        show_api_error(error)
        st.button('Retry', on_click=reset_map_date)
