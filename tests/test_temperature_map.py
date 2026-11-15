from itertools import product

import pytest

pytest.importorskip("streamlit")

from frontend.components.body_map import PARTS, RESOURCES, map_filename, temperature_color


@pytest.mark.parametrize('temperature,color', [(34.49, 'R'), (34.5, 'Y'), (35.49, 'Y'),
    (35.5, 'G'), (37, 'G'), (37.01, 'Y'), (38.9, 'Y'), (39, 'Y'), (39.01, 'R')])
def test_temperature_boundaries(temperature, color):
    assert temperature_color(temperature) == color


def test_map_uses_worst_side_and_requires_all_regions():
    readings = {part: {'temperatura': 36} for part in PARTS}
    readings['Right arm']['temperatura'] = 40
    readings['Left leg']['temperatura'] = 35
    assert map_filename(readings) == 'HG_AR_LY.png'
    del readings['Neck']
    assert map_filename(readings) is None


def test_all_color_combinations_have_images():
    for head, arms, legs in product('GYR', repeat=3):
        assert (RESOURCES / f'H{head}_A{arms}_L{legs}.png').is_file()


@pytest.mark.parametrize('part,bounds', [
    ('Neck', (7, 15, 40, 60)),
    ('Left arm', (5, 10, 30, 50)), ('Right arm', (5, 10, 30, 50)),
    ('Left leg', (2, 5, 20, 35)), ('Right leg', (2, 5, 20, 35)),
])
def test_microcirculation_thresholds(part, bounds):
    from frontend.components.body_map import caudal_color
    low, normal_low, normal_high, high = bounds
    for value, color in [(low - .01, 'R'), (low, 'Y'),
                         (normal_low - .01, 'Y'), (normal_low, 'G'),
                         (normal_high, 'G'), (normal_high + .01, 'Y'),
                         (high, 'Y'), (high + .01, 'R')]:
        assert caudal_color(value, part) == color


def test_microcirculation_page_uses_flow_not_temperature(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from frontend.components import body_map
    readings = {part: {'nombre': part, 'temperatura': 36, 'caudal': 20,
                        'timestamp': '2020-01-02T12:00:00Z', 'movimiento': 0}
                for part in PARTS}
    readings['Neck']['caudal'] = 61
    readings['Left arm']['caudal'] = 7
    assert map_filename(readings, 'caudal') == 'HR_AY_LG.png'
    assert map_filename(readings) == 'HG_AG_LG.png'
    monkeypatch.setattr(body_map.api, 'read', lambda *args, **kwargs:
        {'date': '2020-01-02', 'items': list(readings.values())})
    app = AppTest.from_string('from frontend.views.microcirculation import render_microcirculation\nrender_microcirculation()')
    app.session_state['access_token'] = 'test'
    app.run()
    assert not app.exception
    html = '\n'.join(element.value for element in app.get('html'))
    assert 'Microcirculation color legend' in html
    assert 'body-map-image' in html
    assert 'Green — Normal: Within the expected reference range.' in html
    table = app.table[0].value.set_index('Body region')
    assert table.loc['Neck', 'Microcirculation (PU)'] == 61
    assert table.loc['Neck', 'Status'] == 'Alert'
    assert app.date_input[0].value.isoformat() == '2020-01-02'
