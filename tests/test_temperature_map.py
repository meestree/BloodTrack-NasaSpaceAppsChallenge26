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
    readings['Brazo derecho']['temperatura'] = 40
    readings['Pierna izquierda']['temperatura'] = 35
    assert map_filename(readings) == 'HG_AR_LY.png'
    del readings['Cuello']
    assert map_filename(readings) is None


def test_all_color_combinations_have_images():
    for head, arms, legs in product('GYR', repeat=3):
        assert (RESOURCES / f'H{head}_A{arms}_L{legs}.png').is_file()


@pytest.mark.parametrize('part,value,color', [
    ('Cuello', 299, 'R'), ('Cuello', 300, 'Y'), ('Cuello', 699, 'Y'),
    ('Cuello', 700, 'G'), ('Cuello', 849, 'G'), ('Cuello', 850, 'Y'),
    ('Cuello', 950, 'Y'), ('Cuello', 951, 'R'),
    ('Brazo izquierdo', 299, 'R'), ('Brazo izquierdo', 300, 'Y'),
    ('Brazo izquierdo', 749.99, 'Y'), ('Brazo izquierdo', 750, 'G'),
    ('Brazo izquierdo', 751, 'G'), ('Pierna derecha', 1000, 'G'),
    ('Pierna derecha', 1000.01, 'Y'), ('Pierna derecha', 1499, 'Y'), ('Pierna derecha', 1500, 'Y'),
    ('Pierna derecha', 20000, 'Y'), ('Pierna derecha', 20001, 'R'),
])
def test_microcirculation_thresholds(part, value, color):
    from frontend.components.body_map import caudal_color
    assert caudal_color(value, part) == color


def test_microcirculation_page_uses_flow_not_temperature(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from frontend.components import body_map
    readings = {part: {'nombre': part, 'temperatura': 36, 'caudal': 800,
                        'timestamp': '2020-01-02T12:00:00Z', 'movimiento': 0}
                for part in PARTS}
    readings['Cuello']['caudal'] = 960
    readings['Brazo izquierdo']['caudal'] = 500
    assert map_filename(readings, 'caudal') == 'HR_AY_LG.png'
    assert map_filename(readings) == 'HG_AG_LG.png'
    monkeypatch.setattr(body_map, 'request', lambda *args, **kwargs:
        {'date': '2020-01-02', 'items': list(readings.values())})
    app = AppTest.from_string('from frontend.views.microcirculation import render_microcirculation\nrender_microcirculation()')
    app.session_state['access_token'] = 'test'
    app.run()
    assert not app.exception
    html = '\n'.join(element.value for element in app.get('html'))
    assert 'Microcirculation color legend' in html
    assert 'body-map-image' in html
    assert 'Green — Normal: Within the expected reference range.' in html
    assert any('960.00' in element.value and 'Alert' in element.value for element in app.markdown)
    assert app.date_input[0].value.isoformat() == '2020-01-02'
