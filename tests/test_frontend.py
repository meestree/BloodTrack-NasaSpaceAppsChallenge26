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
            (1, 'Neck'), (2, 'Left arm'), (3, 'Right arm'),
            (4, 'Left leg'), (5, 'Right leg')])
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
         'caudal': 20, 'movimiento': n % 2} for n in range(count)]})


def test_index_login_registration_and_about(connected):
    screen = app()
    assert [field.label for field in screen.text_input] == ['User', 'Password']
    assert any('WELCOME TO BLOODTRACK' in item.value for item in screen.markdown)
    assert not any('Our vision' in item.value for item in screen.get('html'))
    assert not any(item.label == 'About Us' for item in screen.button)
    screen = app('about')
    assert screen.query_params['page'] == 'about'
    about = '\n'.join(item.value for item in screen.get('html'))
    assert 'About Us' in about and 'Our vision' in about and 'Features' in about
    screen.button(key='back_home').click().run()
    assert screen.query_params['page'] == 'home'
    button(screen, 'Get started').click().run()
    assert screen.query_params['page'] == 'signup'
    screen.button(key='signup_login').click().run()
    assert not screen.exception
    assert any('WELCOME TO BLOODTRACK' in item.value for item in screen.markdown)


def test_workspace_combines_mission_and_features(signed_in):
    _, _, token, _ = signed_in
    screen = app('welcome', token=token)
    assert any(item.label == 'About Us' for item in screen.button)
    assert not any(item.label in ('Our Mission', 'Features') for item in screen.button)
    about = '\n'.join(item.value for item in screen.get('html'))
    assert 'Our vision' in about and 'Features' in about


def test_registration_login_logout(connected):
    client, calls = connected
    screen = app('signup')
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value('astronaut@example.com')
    screen.text_input[2].set_value(PASSWORD)
    screen.selectbox(key='birth_year').select(1995)
    screen.selectbox(key='birth_month').select(5)
    screen.selectbox(key='birth_day').select(21)
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
    screen.selectbox(key='birth_year').select(1995)
    screen.selectbox(key='birth_month').select(5)
    screen.selectbox(key='birth_day').select(21)
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

    ('daily', '/measurements/daily'),
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
                                     'daily'])
def test_pages_show_empty_data_without_crashing(signed_in, section):
    _, _, token, _ = signed_in
    screen = app('welcome', section, token)
    if section == 'analysis':
        screen.button(key='analysis-temperature').click().run()
    assert not screen.exception
    assert any('No measurements' in row.value for row in screen.info)
    assert not screen.error


@pytest.mark.parametrize('section', ['temperature', 'microcirculation', 'reliability', 'analysis',
                                     'daily'])
def test_protected_pages_redirect_without_session(section):
    screen = app('welcome', section)
    assert screen.query_params['page'] == 'login'
    assert screen.warning


def test_revoked_token_clears_user_data_and_redirects(signed_in):
    client, _, token, user = signed_in
    screen = app('welcome', 'daily', token)
    screen.session_state['user'] = user
    screen.session_state['map_date'] = date(2020, 1, 2)
    api.logout(token)
    screen.run()
    assert not screen.exception
    assert screen.query_params['page'] == 'login'
    assert 'access_token' not in screen.session_state
    assert 'user' not in screen.session_state
    assert 'map_date' not in screen.session_state
    assert 'daily_days' not in screen.session_state


def test_login_validation_and_connection_error(connected, monkeypatch):
    screen = app('login')
    button(screen, 'Log In').click().run()
    assert screen.error[0].value == 'Enter your user and password.'
    screen.text_input[0].set_value('astronaut')
    screen.text_input[1].set_value(PASSWORD)
    def unavailable(*args, **kwargs):
        raise api.requests.ConnectionError()
    monkeypatch.setattr(api, '_send', unavailable)
    button(screen, 'Log In').click().run()
    assert not screen.exception
    assert 'Cannot reach' in screen.error[0].value
    assert 'access_token' not in screen.session_state


def test_about_navigation_still_works():
    screen = app('welcome')
    screen.button(key='section_about').click().run()
    assert not screen.exception
    assert 'About Us' in ' '.join(row.value for row in screen.get('html'))


def test_map_navigation_reuses_readings_and_refreshes_on_demand(signed_in):
    _, calls, token, _ = signed_in
    seed(token)
    calls.clear()
    screen = app('welcome', 'temperature', token)
    assert [(method, path) for method, path, _ in calls] == [('GET', '/api/v1/measurements/latest')]
    calls.clear()
    screen.button(key='navigation_open').click().run()
    assert [(method, path) for method, path, _ in calls] == [('GET', '/api/v1/auth/me')]
    calls.clear()
    button(screen, 'Latest readings').click().run()
    assert [(method, path) for method, path, _ in calls] == [('GET', '/api/v1/measurements/latest')]
    assert not screen.exception
