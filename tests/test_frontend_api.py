"""Client configuration, response handling, and display-safe validation messages."""
from unittest.mock import Mock

import pytest

pytest.importorskip('requests')
from frontend import api


@pytest.mark.parametrize('setting', ['API_BASE_URL', 'NASA_API_URL'])
def test_configured_base_url_used_for_auth_and_data(monkeypatch, setting):
    monkeypatch.delenv('API_BASE_URL', raising=False)
    monkeypatch.delenv('NASA_API_URL', raising=False)
    monkeypatch.setenv(setting, 'http://api.test/api/v1/')
    send = Mock(return_value=Mock(ok=True, status_code=200, json=lambda: {'items': []}))
    monkeypatch.setattr(api.requests, 'request', send)
    for path in ['/auth/me', '/measurements']:
        api.request('GET', path, 'private-token')
        assert send.call_args.args[1] == 'http://api.test/api/v1' + path
        assert send.call_args.kwargs['headers']['Authorization'] == 'Bearer private-token'


def test_logout_handles_empty_204(monkeypatch):
    response = Mock(ok=True, status_code=204)
    monkeypatch.setattr(api.requests, 'request', Mock(return_value=response))
    assert api.logout('private-token') is None
    response.json.assert_not_called()


def test_validation_details_map_to_fields_without_echoing_values(monkeypatch):
    response = Mock(ok=False, status_code=422, json=lambda: {'detail': [
        {'loc': ['body', 'measurements', 0, 'timestamp'], 'msg': 'sensitive input', 'type': 'value_error'},
        {'loc': ['body', 'password'], 'msg': 'private-password', 'type': 'value_error'}]})
    monkeypatch.setattr(api.requests, 'request', Mock(return_value=response))
    with pytest.raises(api.ApiError) as caught:
        api.request('POST', '/measurements')
    assert set(caught.value.fields) == {'timestamp', 'password'}
    assert 'sensitive input' not in str(caught.value.fields)
    assert 'private-password' not in str(caught.value.fields)


def test_malformed_json_has_visible_safe_error(monkeypatch):
    response = Mock(ok=True, status_code=200)
    response.json.side_effect = ValueError('sensitive response body')
    monkeypatch.setattr(api.requests, 'request', Mock(return_value=response))
    with pytest.raises(api.ApiError, match='invalid response'):
        api.request('GET', '/measurements')
