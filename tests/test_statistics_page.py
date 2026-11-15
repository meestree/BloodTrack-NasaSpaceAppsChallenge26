import pytest
pytest.importorskip('streamlit')
from frontend.components import statistics_chart


def sample_data(metric='temperatura', end='2020-01-02'):
    return {'from': '2020-01-02', 'to': end, 'metric': metric,
            'granularity': 'hour' if end == '2020-01-02' else 'day',
            'items': [{'id_parte': 1, 'nombre': 'Neck',
                       'periodo': '2020-01-02T10:00:00Z' if end == '2020-01-02' else '2020-01-02',
                       'media': 36 if metric == 'temperatura' else 20,
                       'muestras': 2, 'desviacion_estandar': 1, 'minimo': 35, 'maximo': 37}]}


def test_statistics_charts_keep_gaps_and_reference_limits():
    rows = statistics_chart.chart_rows(sample_data(), ('Neck',))
    assert len(rows) == 24
    assert rows[9]['Mean'] is None and rows[9]['Samples'] is None
    assert rows[10]['Mean'] == 36 and rows[10]['Lower'] == 35
    for metric in ('temperatura', 'caudal'):
        spec = statistics_chart.make_chart(sample_data(metric), ('Neck',), metric).to_dict()
        assert spec['layer'][1]['mark']['invalid'] == 'break-paths-show-domains'
        assert len(spec['layer']) == 4
        assert spec['layer'][2]['mark']['color'] == '#f5cf36'
        assert spec['layer'][3]['mark']['color'] == '#e44838'
        for layer, expected in zip(spec['layer'][2:], statistics_chart.thresholds(metric, ('Neck',))):
            values = layer['data']['values']
            assert [row['Threshold'] for row in values] == list(expected)
        assert not spec.get('params')


def test_buttons_switch_metric_and_date_granularity(monkeypatch):
    from datetime import date
    from streamlit.testing.v1 import AppTest
    calls = []
    def api(path, token=None, **kwargs):
        if path.endswith('latest'):
            return {'date': '2020-01-02', 'items': []}
        params = kwargs['params']
        calls.append(params)
        return sample_data(params['metric'], params['end_date'])
    monkeypatch.setattr(statistics_chart, 'read', api)
    app = AppTest.from_string('from frontend.views.statistical_analysis import render_statistical_analysis\nrender_statistical_analysis()', default_timeout=20)
    app.session_state['access_token'] = 'test'
    app.run()
    assert not app.exception and len(app.date_input) == 0
    app.button(key='analysis-temperature').click().run()
    assert not app.exception
    assert calls[-1]['metric'] == 'temperatura'
    assert not app.expander and not app.caption
    app.date_input[0].set_value((date(2020, 1, 2), date(2020, 1, 4))).run()
    assert not app.exception
    assert calls[-1]['end_date'] == '2020-01-04'
    app.date_input[0].set_value((date(2020, 1, 3),)).run()
    assert not app.exception
    assert calls[-1]['start_date'] == '2020-01-02'
    assert calls[-1]['end_date'] == '2020-01-04'
    assert not app.expander and not app.caption
    app.button(key='analysis-microcirculation').click().run()
    assert not app.exception
    assert calls[-1]['metric'] == 'caudal' and calls[-1]['end_date'] == '2020-01-04'


@pytest.mark.parametrize('group', ['Arms', 'Legs'])
def test_limb_series_pool_samples_and_variance(group):
    parts = statistics_chart.GROUPS[group]
    data = sample_data()
    data['items'] = [
        {'nombre': parts[0], 'periodo': '2020-01-02T10:00:00Z',
         'media': 10, 'muestras': 1, 'desviacion_estandar': None},
        {'nombre': parts[1], 'periodo': '2020-01-02T10:00:00Z',
         'media': 20, 'muestras': 3, 'desviacion_estandar': 2},
    ]
    rows = statistics_chart.chart_rows(data, parts)
    assert len(rows) == 24
    assert {row['Region'] for row in rows} == {group}
    assert rows[9]['Mean'] is None
    assert rows[10]['Mean'] == 17.5 and rows[10]['Samples'] == 4
    assert rows[10]['SD'] == pytest.approx((83 / 3) ** .5)
    data['items'] = data['items'][:1]
    single = statistics_chart.chart_rows(data, parts)[10]
    assert single['Mean'] == 10 and single['SD'] is None


@pytest.mark.parametrize('parts,caution,danger', [
    (('Neck',), (15, 40), (7, 60)),
    (('Left arm', 'Right arm'), (10, 30), (5, 50)),
    (('Left leg', 'Right leg'), (5, 20), (2, 35)),
])
def test_pu_chart_thresholds(parts, caution, danger):
    assert statistics_chart.thresholds('caudal', parts) == (caution, danger)
