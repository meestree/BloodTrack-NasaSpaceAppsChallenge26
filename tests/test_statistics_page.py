import pytest
pytest.importorskip('streamlit')
from frontend.components import statistics_chart


def sample_data(metric='temperatura', end='2020-01-02'):
    return {'from': '2020-01-02', 'to': end, 'metric': metric,
            'granularity': 'hour' if end == '2020-01-02' else 'day',
            'items': [{'id_parte': 1, 'nombre': 'Cuello',
                       'periodo': '2020-01-02T10:00:00Z' if end == '2020-01-02' else '2020-01-02',
                       'media': 36 if metric == 'temperatura' else 750,
                       'muestras': 2, 'desviacion_estandar': 1, 'minimo': 35, 'maximo': 37}]}


def test_statistics_charts_keep_gaps_and_reference_limits():
    rows = statistics_chart.chart_rows(sample_data(), ('Cuello',))
    assert len(rows) == 24
    assert rows[9]['Mean'] is None and rows[9]['Samples'] is None
    assert rows[10]['Mean'] == 36 and rows[10]['Lower'] == 35
    for metric in ('temperatura', 'caudal'):
        spec = statistics_chart.make_chart(sample_data(metric), ('Cuello',), metric).to_dict()
        assert spec['layer'][1]['mark']['invalid'] == 'break-paths-show-domains'
        assert len(spec['layer']) == 3


def test_buttons_switch_metric_and_date_granularity(monkeypatch):
    from datetime import date
    from streamlit.testing.v1 import AppTest
    calls = []
    def api(method, path, token=None, **kwargs):
        if path.endswith('latest'):
            return {'date': '2020-01-02', 'items': []}
        params = kwargs['params']
        calls.append(params)
        return sample_data(params['metric'], params['end_date'])
    monkeypatch.setattr(statistics_chart, 'request', api)
    app = AppTest.from_string('from frontend.views.statistical_analysis import render_statistical_analysis\nrender_statistical_analysis()', default_timeout=20)
    app.session_state['access_token'] = 'test'
    app.run()
    assert not app.exception and len(app.date_input) == 0
    app.button(key='analysis-temperature').click().run()
    assert not app.exception
    assert calls[-1]['metric'] == 'temperatura'
    assert any('Mean per UTC hour' in item.value for item in app.caption)
    app.date_input[0].set_value((date(2020, 1, 2), date(2020, 1, 4))).run()
    assert not app.exception
    assert any('Mean per UTC day' in item.value for item in app.caption)
    app.button(key='analysis-microcirculation').click().run()
    assert not app.exception
    assert calls[-1]['metric'] == 'caudal' and calls[-1]['end_date'] == '2020-01-04'
