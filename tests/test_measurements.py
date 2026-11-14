from datetime import datetime, timedelta, timezone

import pytest

from backend.api.auth import current_user
from backend.auth.schemas import UserResponse


@pytest.fixture
def measured(client):
    store = client.app.state.auth_store
    with store.connection() as c:
        c.execute("INSERT INTO usuarios (nombre_usuario,password_hash,email,fecha_nacimiento) VALUES ('one','unused','one@example.com','1990-01-01')")
        c.execute("INSERT INTO usuarios (nombre_usuario,password_hash,email,fecha_nacimiento) VALUES ('two','unused','two@example.com','1990-01-01')")
        c.executemany("INSERT INTO partes_corporales VALUES (?, ?)", [(1, 'Cuello'), (2, 'Brazo izquierdo')])
        user = dict(c.execute("SELECT * FROM vista_usuarios WHERE id_usuario = 1").fetchone())
    client.app.dependency_overrides[current_user] = lambda: UserResponse(**user)
    yield client, user
    client.app.dependency_overrides.clear()


def item(part=1, temperature=30, flow=10, movement=0, at=None):
    return {"id_parte": part, "temperatura": temperature, "caudal": flow,
            "movimiento": movement, "timestamp": (at or datetime.now(timezone.utc)).isoformat()}


def post(client, items):
    return client.post('/api/v1/measurements', json={"measurements": items})


def test_collection_history_and_means(measured):
    client, _ = measured
    assert post(client, [item(), item(temperature=34, flow=20, movement=1)]).status_code == 201
    history = client.get('/api/v1/measurements?days=1').json()
    assert history['total'] == 2
    assert {r['temperatura'] for r in history['items']} == {30, 34}
    daily = client.get('/api/v1/measurements/daily?days=1').json()['items'][0]
    assert daily['temperatura_media'] == 32
    assert daily['caudal_media'] == 15
    assert daily['muestras'] == 2
    assert daily['movimiento_unos'] == 1
    with client.app.state.auth_store.connection() as c:
        assert c.execute('SELECT temperatura_media FROM resumenes_diarios').fetchone()[0] == 32
    stats = client.get('/api/v1/measurements/analytics?days=2').json()['items'][0]
    assert stats['movimiento_fraccion'] == 0.5
    assert stats['temperatura_min'] == 30
    assert stats['temperatura_max'] == 34
    assert stats['dias_sin_datos'] == 1
    assert stats['cobertura_dias_fraccion'] == 0.5


def test_days_pagination_and_body_filter(measured):
    client, _ = measured
    old = datetime.now(timezone.utc) - timedelta(days=10)
    post(client, [item(at=old), item(), item(part=2)])
    assert client.get('/api/v1/measurements?days=1').json()['total'] == 2
    result = client.get('/api/v1/measurements?days=30&id_parte=1&limit=1&offset=1').json()
    assert result['total'] == 2
    assert len(result['items']) == 1
    assert result['items'][0]['id_parte'] == 1
    assert len(client.get('/api/v1/measurements/daily?days=30&id_parte=1').json()['items']) == 2


def test_users_cannot_access_each_others_data(measured):
    client, user = measured
    post(client, [item()])
    user['id_usuario'] = 2
    assert client.get('/api/v1/measurements').json()['total'] == 0
    assert client.get('/api/v1/measurements/daily').json()['items'] == []
    assert client.get('/api/v1/measurements/analytics').json()['items'] == []
    post(client, [item(temperature=99)])
    assert client.get('/api/v1/measurements').json()['items'][0]['id_usuario'] == 2


def test_batch_is_atomic_for_unknown_part(measured):
    client, _ = measured
    assert post(client, [item(), item(part=999)]).status_code == 422
    assert client.get('/api/v1/measurements').json()['total'] == 0


@pytest.mark.parametrize('change', [
    {'movimiento': 2}, {'temperatura': 'NaN'}, {'caudal': 'Infinity'},
    {'timestamp': '2020-01-01T12:00:00'}, {'id_usuario': 2},
    {'timestamp': '2999-01-01T00:00:00Z'},
])
def test_invalid_payload(measured, change):
    client, _ = measured
    row = item()
    row.update(change)
    assert post(client, [row]).status_code == 422


def test_weighted_period_mean_and_backdated_updates(measured):
    client, _ = measured
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    post(client, [item(temperature=20, at=yesterday), item(temperature=40), item(temperature=40)])
    stats = client.get('/api/v1/measurements/analytics?days=2').json()['items'][0]
    assert stats['temperatura_media'] == pytest.approx(100 / 3)
    post(client, [item(temperature=30, at=yesterday)])
    daily = client.get('/api/v1/measurements/daily?days=2').json()['items']
    assert daily[0]['temperatura_media'] == 25
    assert daily[0]['muestras'] == 2
    client.app.state.measurement_store.initialize()
    assert client.get('/api/v1/measurements/daily?days=2').json()['items'] == daily


def test_all_routes_require_authentication(client):
    for path in ['/body-parts', '/measurements', '/measurements/daily', '/measurements/analytics']:
        assert client.get('/api/v1' + path).status_code == 401
    assert post(client, [item()]).status_code == 401


def test_invalid_window_and_body_parts(measured):
    client, _ = measured
    assert len(client.get('/api/v1/body-parts').json()) == 2
    for query in ['days=0', 'days=3651', 'limit=1001', 'offset=-1']:
        assert client.get('/api/v1/measurements?' + query).status_code == 422


def test_latest_by_utc_date_and_user(measured):
    client, user = measured
    old = datetime(2020, 1, 2, 10, tzinfo=timezone.utc)
    post(client, [item(at=old, temperature=36), item(part=2, at=old, temperature=39.5),
                  item(at=old + timedelta(hours=1), temperature=37)])
    data = client.get('/api/v1/measurements/latest').json()
    assert data['date'] == '2020-01-02'
    assert [row['temperatura'] for row in data['items']] == [37, 39.5]
    assert data['items'][0]['nombre'] == 'Cuello'
    assert client.get('/api/v1/measurements/latest?date=2020-01-03').json()['items'] == []
    assert client.get('/api/v1/measurements/latest?date=bad').status_code == 422
    user['id_usuario'] = 2
    assert client.get('/api/v1/measurements/latest').json() == {'date': None, 'items': []}
    client.app.dependency_overrides.clear()
    assert client.get('/api/v1/measurements/latest').status_code == 401


def test_latest_timestamp_offsets_and_ties(measured):
    client, _ = measured
    with client.app.state.auth_store.connection() as c:
        c.executemany('''INSERT INTO registros
            (id_usuario,id_parte,timestamp,temperatura,caudal,movimiento) VALUES (1,1,?,?,750,0)''',
            [('2020-01-03T00:30:00+02:00', 35),
             ('2020-01-02T23:00:00Z', 36), ('2020-01-02T23:00:00Z', 37)])
    result = client.get('/api/v1/measurements/latest?date=2020-01-02').json()
    assert result['items'][0]['temperatura'] == 37


def test_streamlit_map_loads_api_and_changes_date(measured, monkeypatch):
    pytest.importorskip('streamlit')
    from streamlit.testing.v1 import AppTest
    from frontend.components import body_map
    from frontend.services.api import ApiError
    client, _ = measured
    with client.app.state.auth_store.connection() as c:
        c.executemany('INSERT INTO partes_corporales VALUES (?,?)',
            [(3, 'Brazo derecho'), (4, 'Pierna izquierda'), (5, 'Pierna derecha')])
    at = datetime(2020, 1, 2, 12, tzinfo=timezone.utc)
    post(client, [item(part=p, temperature=36, at=at) for p in range(1, 6)])

    def api(method, path, token=None, **kwargs):
        response = client.request(method, '/api/v1' + path, **kwargs)
        if response.status_code == 401:
            raise ApiError('Expired', 401)
        assert response.status_code == 200
        return response.json()

    monkeypatch.setattr(body_map, 'request', api)
    from pathlib import Path
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'src/frontend/app.py', default_timeout=20)
    app.session_state['access_token'] = 'test-session'
    app.run()
    assert not app.exception
    assert app.date_input[0].value.isoformat() == '2020-01-02'
    assert any('body-map-image' in element.value for element in app.get('html'))
    app.date_input[0].set_value(datetime(2020, 1, 3).date()).run()
    assert not app.exception
    assert any('No measurements' in element.value for element in app.info)
    client.app.dependency_overrides.clear()
    app.run()
    assert not app.exception
    assert len(app.text_input) == 2


def test_movement_hourly_daily_and_user_isolation(measured):
    client, user = measured
    first = datetime(2020, 1, 2, 10, tzinfo=timezone.utc)
    post(client, [item(at=first, movement=1), item(at=first, movement=0),
                  item(at=first + timedelta(hours=1), movement=0),
                  item(at=first + timedelta(days=1), movement=1)])
    path = '/api/v1/measurements/movement'
    single = client.get(path, params={'start_date': '2020-01-02', 'end_date': '2020-01-02'}).json()
    assert single['granularity'] == 'hour'
    assert single['items'] == [
        {'periodo': '2020-01-02T10:00:00Z', 'muestras': 2, 'movimiento_unos': 1},
        {'periodo': '2020-01-02T11:00:00Z', 'muestras': 1, 'movimiento_unos': 0}]
    query = {'start_date': '2020-01-02', 'end_date': '2020-01-04'}
    daily = client.get(path, params=query).json()
    assert daily['granularity'] == 'day'
    assert [row['movimiento_unos'] for row in daily['items']] == [1, 1]
    assert len(daily['items']) == 2  # Unsampled Jan 4 is omitted.
    assert client.get(path, params={**query, 'id_parte': 2}).json()['items'] == []
    for start, end in [('2020-01-03', '2020-01-02'), ('2000-01-01', '2020-01-01'),
                       ('2999-01-01', '2999-01-02'), ('invalid', '2020-01-02')]:
        assert client.get(path, params={'start_date': start, 'end_date': end}).status_code == 422
    user['id_usuario'] = 2
    assert client.get(path, params=query).json()['items'] == []
    client.app.dependency_overrides.clear()
    assert client.get(path, params=query).status_code == 401


def test_statistics_hourly_daily_metrics_and_isolation(measured):
    client, user = measured
    at = datetime(2020, 1, 2, 10, tzinfo=timezone.utc)
    post(client, [item(at=at, temperature=36, flow=750),
                  item(at=at, temperature=38, flow=850),
                  item(at=at + timedelta(hours=1), temperature=34, flow=700),
                  item(part=2, at=at, temperature=35)])
    path = '/api/v1/measurements/statistics'
    params = {'start_date': '2020-01-02', 'end_date': '2020-01-02'}
    data = client.get(path, params=params).json()
    assert data['granularity'] == 'hour'
    row = data['items'][0]
    assert row['media'] == 37
    assert row['desviacion_estandar'] == pytest.approx(2 ** .5)
    assert row['minimo'] == 36 and row['maximo'] == 38
    assert data['items'][1]['desviacion_estandar'] is None
    flow = client.get(path, params={**params, 'metric': 'caudal'}).json()
    assert flow['items'][0]['media'] == 800
    assert flow['items'][0]['desviacion_estandar'] == pytest.approx(5000 ** .5)
    daily = client.get(path, params={**params, 'end_date': '2020-01-04'}).json()
    assert daily['granularity'] == 'day'
    assert daily['items'][0]['media'] == 36
    assert daily['items'][0]['desviacion_estandar'] == 2
    assert daily['items'][0]['muestras'] == 3
    for changes in [{'metric': 'bad'}, {'end_date': '2020-01-01'},
                    {'end_date': '2999-01-01'}, {'start_date': '1900-01-01'}]:
        assert client.get(path, params={**params, **changes}).status_code == 422
    user['id_usuario'] = 2
    assert client.get(path, params=params).json()['items'] == []
    client.app.dependency_overrides.clear()
    assert client.get(path, params=params).status_code == 401
