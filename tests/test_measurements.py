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
