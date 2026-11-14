"""Body maps driven exclusively by authenticated API measurements."""
from base64 import b64encode
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st

from frontend.components.session import require_session, show_api_error
from frontend.api import ApiError, request

RESOURCES = Path(__file__).resolve().parents[2] / 'resources'
PARTS = ('Cuello', 'Brazo izquierdo', 'Brazo derecho', 'Pierna izquierda', 'Pierna derecha')


def temperature_color(value: float) -> str:
    if value < 34.5 or value > 39:
        return 'R'
    if 35.5 <= value <= 37:
        return 'G'
    # Includes 34.5 and the unspecified 38.9–39 gap as caution.
    return 'Y'


def caudal_color(value: float, part: str) -> str:
    if value < 300 or value > (950 if part == 'Cuello' else 20000):
        return 'R'
    if part == 'Cuello':
        return 'Y' if value < 700 or value >= 850 else 'G'
    return 'G' if 750 <= value <= 1000 else 'Y'


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


def render_body_map(metric: str = 'temperatura') -> None:
    label = 'Microcirculation' if metric == 'caudal' else 'Temperature'
    token = require_session()
    try:
        with st.spinner(f'Loading {label.lower()} measurements…'):
            if not st.session_state.get('map_date_initialized'):
                latest = request('GET', '/measurements/latest', token)
                st.session_state.map_date = date.fromisoformat(latest['date']) if latest['date'] else datetime.now(timezone.utc).date()
                st.session_state.map_date_initialized = True
            if st.button('Latest readings'):
                st.session_state.map_date_initialized = False
                st.rerun()
            selected = st.date_input('Measurement date (UTC)', max_value=datetime.now(timezone.utc).date(), key='map_date')
            data = request('GET', '/measurements/latest', token, params={'date': selected.isoformat()})
        readings = {row['nombre']: row for row in data['items']}
        if not readings:
            st.info('No measurements recorded on this UTC date.')
            return
        filename = map_filename(readings, metric)
        if filename:
            image = RESOURCES / filename
            if image.is_file():
                encoded = b64encode(image.read_bytes()).decode('ascii')
                st.html(f'<div class="body-map-frame"><img class="body-map-image" src="data:image/png;base64,{encoded}" alt="{label} map: neck, arms and legs. Individual readings and statuses are listed below."></div>')
            else:
                st.error('The body map image is unavailable.')
        else:
            st.warning('Some regions have no measurements for this date. The map is unavailable until all five regions have readings.')
        st.caption('Latest reading per region on the selected UTC date. Arms and legs use the more severe reading of the pair.')
        st.caption('Values are shown as reported by the API; sensor units are not specified. Colors use the existing design reference ranges.')
        status = {'G': 'Normal', 'Y': 'Warning', 'R': 'Alert'} if metric == 'caudal' else {'G': 'Normal', 'Y': 'Caution', 'R': 'Danger'}
        for part in dict.fromkeys((*PARTS, *readings)):
            row = readings.get(part)
            if row:
                st.write(f"**{part}** · {row[metric]:.2f} · {status[reading_color(row, part, metric)]}")
                st.caption(f"Recorded: {row['timestamp']} · Caudal: {row['caudal']} · Movement: {bool(row['movimiento'])}")
            else:
                st.write(f'**{part}** · No measurement')
    except ApiError as error:
        show_api_error(error)
        if st.button('Retry'):
            st.rerun()
