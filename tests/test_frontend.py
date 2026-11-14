"""Run real Streamlit page flows against the FastAPI application and a temporary DB."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip('streamlit')
from streamlit.testing.v1 import AppTest

from frontend import api

APP = Path(__file__).resolve().parents[1] / 'src/frontend/app.py'
PASSWORD = 'frontend-test-password'


@pytest.fixture
def connected(client, frontend_requests):
    calls = frontend_requests
    with client.app.state.auth_store.connection() as connection:
        connection.executemany('INSERT INTO partes_corporales VALUES (?, ?)', [
            (1, 'Cuello'), (2, 'Brazo izquierdo'), (3, 'Brazo derecho'),
            (4, 'Pierna izquierda'), (5, 'Pierna derecha')])
    return client, calls


@pytest.fixture
def signed_in(connected):
    client, calls = connected
    api.request('POST', '/auth/register', json={
        'nombre_usuario': 'astronaut', 'password': PASSWORD,
        'email': 'astronaut@example.com', 'fecha_nacimiento': '1995-05-21'})
    token, user = api.login('astronaut', PASSWORD)
    return client, calls, token, user


def app(page='home', section=None, token=None):
    result = AppTest.from_file(APP, default_timeout=20)
    result.query_params['page'] = page
    if section:
        result.query_params['section'] = section
    if token:
        result.session_state['access_token'] = token
    result.run()
    assert not result.exception
    return result


def button(screen, label):
    return next(item for item in screen.button if item.label == label)


def seed(token, count=5):
    at = datetime.now(timezone.utc) - timedelta(seconds=5)
    api.request('POST', '/measurements', token, json={'measurements': [
        {'id_parte': n % 5 + 1, 'timestamp': at.isoformat(), 'temperatura': 36,
         'caudal': 800, 'movimiento': n % 2} for n in range(count)]})


def test_home_forms_and_api_health(connected):
    for label, page in [('Log In', 'login'), ('Get started', 'signup')]:
        screen = app()
        button(screen, label).click().run()
        assert screen.query_params['page'] == page
        assert not screen.exception
    screen = app()
    button(screen, 'Check API connection').click().run()
    assert screen.success[0].value == 'The API is available.'


def test_registration_login_profile_logout(connected):
    client, calls = connected
    screen = app('signup')
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value('astronaut@example.com')
    screen.text_input[2].set_value(PASSWORD)
    screen.date_input[0].set_value(date(1995, 5, 21))
    button(screen, 'Sign Up').click().run()
    assert not screen.exception
    assert screen.query_params['page'] == 'login'
    assert 'Account created' in screen.success[0].value
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value(PASSWORD)
    button(screen, 'Log In').click().run()
    assert not screen.exception
    assert screen.query_params['page'] == 'welcome'
    token = screen.session_state['access_token']
    screen.button(key='section_profile').click().run()
    assert not screen.exception
    assert any('astronaut@example.com' in row.value for row in screen.text)
    screen.button(key='navigation_open').click().run()
    screen.button(key='navigation_logout').click().run()
    assert not screen.exception
    assert screen.query_params['page'] == 'login'
    assert 'access_token' not in screen.session_state
    assert 'user' not in screen.session_state
    assert 'section' not in screen.query_params
    assert client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_signup_validation_and_duplicate_errors(connected):
    screen = app('signup')
    button(screen, 'Sign Up').click().run()
    assert len(screen.error) == 4
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value('invalid-email')
    screen.text_input[2].set_value(PASSWORD)
    screen.date_input[0].set_value(date(1995, 5, 21))
    button(screen, 'Sign Up').click().run()
    assert not screen.exception
    assert any('valid value' in row.value for row in screen.error)
    api.request('POST', '/auth/register', json={
        'nombre_usuario': 'astronaut', 'password': PASSWORD,
        'email': 'astronaut@example.com', 'fecha_nacimiento': '1995-05-21'})
    screen.text_input[1].set_value('astronaut@example.com')
    button(screen, 'Sign Up').click().run()
    assert 'already registered' in screen.error[0].value
    assert not screen.success


@pytest.mark.parametrize('section,endpoint', [
    ('temperature', '/measurements/latest'), ('microcirculation', '/measurements/latest'),
    ('reliability', '/measurements/movement'), ('analysis', '/measurements/statistics'),
    ('profile', '/auth/me'), ('collect', '/body-parts'), ('history', '/measurements'),
    ('daily', '/measurements/daily'), ('analytics', '/measurements/analytics'),
])
def test_navigation_opens_real_page_and_endpoint(signed_in, section, endpoint):
    _, calls, token, _ = signed_in
    seed(token)
    screen = app('welcome', token=token)
    screen.button(key=f'section_{section}').click().run()
    if section == 'analysis':
        screen.button(key='analysis-temperature').click().run()
        assert not screen.exception
        screen.button(key='analysis-microcirculation').click().run()
    assert not screen.exception
    assert screen.query_params['section'] == section
    assert not screen.session_state['drawer_is_open']
    assert ('GET', '/api/v1' + endpoint) in [(method, path) for method, path, _ in calls]
    assert not screen.error
    assert not any('coming soon' in row.value for row in screen.markdown)


@pytest.mark.parametrize('section', ['temperature', 'microcirculation', 'reliability', 'analysis',
                                     'history', 'daily', 'analytics'])
def test_pages_show_empty_data_without_crashing(signed_in, section):
    _, _, token, _ = signed_in
    screen = app('welcome', section, token)
    if section == 'analysis':
        screen.button(key='analysis-temperature').click().run()
    assert not screen.exception
    assert any('No measurements' in row.value for row in screen.info)
    assert not screen.error


def test_collection_saves_exact_payload_and_updates_summaries(signed_in):
    _, _, token, _ = signed_in
    screen = app('welcome', 'collect', token)
    button(screen, 'Save measurement').click().run()
    assert len(screen.error) == 3
    screen.number_input(key='measure_temperature').set_value(36.25)
    screen.number_input(key='measure_flow').set_value(810.0)
    screen.selectbox(key='measure_movement').select(1)
    screen.checkbox(key='measure_now').uncheck()
    screen.text_input(key='measure_timestamp').set_value('2020-01-02T12:00:00')
    button(screen, 'Save measurement').click().run()
    assert any('timezone' in row.value for row in screen.error)
    assert api.request('GET', '/measurements', token)['total'] == 0
    screen.checkbox(key='measure_now').check()
    button(screen, 'Save measurement').click().run()
    assert not screen.exception
    assert screen.success
    result = api.request('GET', '/measurements', token)
    assert result['total'] == 1
    row = result['items'][0]
    assert row['temperatura'] == 36.25 and row['caudal'] == 810 and row['movimiento'] == 1
    for path in ('/measurements/daily', '/measurements/analytics'):
        assert api.request('GET', path, token)['items'][0]['muestras'] == 1


def test_history_pagination_filters_and_summaries(signed_in):
    _, calls, token, _ = signed_in
    seed(token, 26)
    screen = app('welcome', 'history', token)
    assert len(screen.dataframe[0].value) == 25
    screen.button(key='history_next').click().run()
    assert not screen.exception
    assert len(screen.dataframe[0].value) == 1
    assert screen.session_state['history_offset'] == 25
    screen.selectbox(key='history_part').select(1).run()
    assert not screen.exception
    assert screen.session_state['history_offset'] == 0
    assert set(screen.dataframe[0].value['id_parte']) == {1}
    assert calls[-1][2]['id_parte'] == 1
    for section, key in (('daily', 'daily'), ('analytics', 'period')):
        screen = app('welcome', section, token)
        screen.number_input(key=f'{key}_days').set_value(1).run()
        screen.selectbox(key=f'{key}_part').select(2).run()
        assert not screen.exception
        assert set(screen.dataframe[0].value['id_parte']) == {2}
        assert calls[-1][2] == {'days': 1, 'id_parte': 2}


@pytest.mark.parametrize('section', ['temperature', 'microcirculation', 'reliability', 'analysis',
                                     'profile', 'collect', 'history', 'daily', 'analytics'])
def test_protected_pages_redirect_without_session(section):
    screen = app('welcome', section)
    assert screen.query_params['page'] == 'login'
    assert screen.warning


def test_revoked_token_clears_user_data_and_redirects(signed_in):
    client, _, token, user = signed_in
    screen = app('welcome', 'history', token)
    screen.session_state['user'] = user
    screen.session_state['map_date'] = date(2020, 1, 2)
    api.logout(token)
    screen.run()
    assert not screen.exception
    assert screen.query_params['page'] == 'login'
    assert 'access_token' not in screen.session_state
    assert 'user' not in screen.session_state
    assert 'map_date' not in screen.session_state
    assert 'history_days' not in screen.session_state


def test_login_validation_and_connection_error(connected, monkeypatch):
    screen = app('login')
    button(screen, 'Log In').click().run()
    assert screen.error[0].value == 'Enter your user and password.'
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value(PASSWORD)
    def unavailable(*args, **kwargs):
        raise api.requests.ConnectionError()
    monkeypatch.setattr(api.requests, 'request', unavailable)
    button(screen, 'Log In').click().run()
    assert not screen.exception
    assert 'Cannot reach' in screen.error[0].value
    assert 'access_token' not in screen.session_state


def test_editorial_navigation_still_works():
    screen = app('welcome')
    for section, title in [('mission', 'OUR MISSION'), ('features', 'FEATURES')]:
        if not screen.session_state['drawer_is_open']:
            screen.button(key='navigation_open').click().run()
        screen.button(key=f'section_{section}').click().run()
        assert not screen.exception
        assert title in ' '.join(row.value for row in screen.markdown)
