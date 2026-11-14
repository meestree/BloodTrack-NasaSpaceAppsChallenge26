import pytest

pytest.importorskip('streamlit')
import pandas as pd

from frontend.components import movement_chart


def test_chart_keeps_missing_periods_unknown():
    data = {'from': '2020-01-02', 'to': '2020-01-02', 'granularity': 'hour',
            'items': [{'periodo': '2020-01-02T10:00:00Z', 'muestras': 4, 'movimiento_unos': 0}]}
    chart = movement_chart.chart_data(data)
    assert len(chart) == 24
    assert chart.iloc[10, 0] == 0
    assert pd.isna(chart.iloc[9, 0])
    data.update({'to': '2020-01-04', 'granularity': 'day',
                 'items': [{'periodo': '2020-01-02', 'muestras': 4, 'movimiento_unos': 2}]})
    chart = movement_chart.chart_data(data)
    assert len(chart) == 3
    assert chart.iloc[0, 0] == 2
    assert pd.isna(chart.iloc[1, 0])


def test_reliability_page_date_range_changes_chart(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from datetime import date
    calls = []

    def api(method, path, token=None, **kwargs):
        if path.endswith('latest'):
            return {'date': '2020-01-02', 'items': []}
        dates = kwargs['params']
        calls.append(dates)
        hourly = dates['start_date'] == dates['end_date']
        return {'from': dates['start_date'], 'to': dates['end_date'],
                'granularity': 'hour' if hourly else 'day',
                'items': [{'periodo': '2020-01-02T10:00:00Z' if hourly else '2020-01-02',
                           'muestras': 10, 'movimiento_unos': 3}]}

    monkeypatch.setattr(movement_chart, 'request', api)
    app = AppTest.from_string('from frontend.views.reliability import render_reliability\nrender_reliability()')
    app.session_state['access_token'] = 'test'
    app.run()
    assert not app.exception
    assert app.metric[0].value == '3'
    assert 'per hour' in app.subheader[0].value
    assert not any('body-map-image' in element.value for element in app.get('html'))
    app.date_input[0].set_value((date(2020, 1, 2), date(2020, 1, 4))).run()
    assert not app.exception
    assert 'per day' in app.subheader[0].value
    assert calls[-1]['end_date'] == '2020-01-04'
