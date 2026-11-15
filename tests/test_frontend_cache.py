"""Request reduction must preserve session isolation, fresh data, and revocation."""
from unittest.mock import Mock

import pytest

pytest.importorskip('streamlit')
from frontend import api


@pytest.fixture
def client_state(monkeypatch):
    state = {}
    now = [100.0]
    send = Mock(return_value=Mock(ok=True, status_code=200, json=lambda: {'items': []}))
    monkeypatch.setattr(api, '_state', lambda: state)
    monkeypatch.setattr(api, '_send', send)
    monkeypatch.setattr(api, 'monotonic', lambda: now[0])
    return state, now, send


def test_cached_rerun_checks_session_once_without_refetching_data(client_state):
    state, _, send = client_state
    api.read('/measurements/daily', 'one')
    api.read('/body-parts', 'one')
    assert send.call_count == 2
    api.begin_run()
    api.read('/measurements/daily', 'one')
    api.read('/body-parts', 'one')
    assert send.call_count == 3
    assert send.call_args.args[1].endswith('/auth/me')


def test_expiry_refresh_and_writes_invalidate_cached_data(client_state):
    _, now, send = client_state
    api.read('/measurements/daily', 'one')
    now[0] += 16
    api.read('/measurements/daily', 'one')
    assert send.call_count == 2
    api.clear_data_cache()
    api.read('/measurements/daily', 'one')
    assert send.call_count == 3
    api.request('POST', '/measurements', 'one', json={'measurements': []})
    api.read('/measurements/daily', 'one')
    assert send.call_count == 5


def test_token_backend_and_browser_sessions_do_not_share_data(client_state, monkeypatch):
    state, _, send = client_state
    api.read('/measurements/daily', 'one')
    api.read('/measurements/daily', 'two')
    monkeypatch.setenv('API_BASE_URL', 'http://other.test/api/v1')
    api.read('/measurements/daily', 'two')
    assert send.call_count == 3
    second_session = {}
    monkeypatch.setattr(api, '_state', lambda: second_session)
    api.read('/measurements/daily', 'two')
    assert send.call_count == 4
    assert second_session['_api_data'] is not state['_api_data']


def test_revoked_session_cannot_read_cached_measurements(client_state):
    state, _, send = client_state
    api.read('/measurements/daily', 'one')
    api.begin_run()
    send.return_value = Mock(ok=False, status_code=401)
    with pytest.raises(api.ApiError) as error:
        api.read('/measurements/daily', 'one')
    assert error.value.status == 401
    assert not state.get('_api_data')


def test_latest_result_is_reused_for_its_selected_date(client_state):
    _, _, send = client_state
    send.return_value.json = lambda: {'date': '2020-01-02', 'items': [{'caudal': 20}]}
    result = api.read('/measurements/latest', 'one')
    result['items'][0]['caudal'] = 999
    dated = api.read('/measurements/latest', 'one', params={'date': '2020-01-02'})
    assert send.call_count == 1
    assert dated['items'][0]['caudal'] == 20


def test_connection_pool_is_private_and_closed_on_logout(monkeypatch):
    state = {}
    monkeypatch.setattr(api, '_state', lambda: state)
    factory = Mock(return_value=Mock())
    monkeypatch.setattr(api.requests, 'Session', factory)
    api._send('GET', 'http://api.test/one')
    api._send('GET', 'http://api.test/two')
    assert factory.call_count == 1
    first = factory.return_value
    second_state = {}
    monkeypatch.setattr(api, '_state', lambda: second_state)
    api._send('GET', 'http://api.test/three')
    assert factory.call_count == 2
    monkeypatch.setattr(api, '_state', lambda: state)
    api.close_client()
    first.close.assert_called_once()
    assert '_api_transport' not in state


def test_failed_requests_are_retried_instead_of_cached(client_state):
    _, _, send = client_state
    send.return_value = Mock(ok=False, status_code=503)
    with pytest.raises(api.ApiError):
        api.read('/measurements/daily', 'one')
    send.return_value = Mock(ok=True, status_code=200, json=lambda: {'items': []})
    assert api.read('/measurements/daily', 'one') == {'items': []}
    assert send.call_count == 2
