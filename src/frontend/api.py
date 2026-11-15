"""One server-side API client for every page; credentials never enter browser URLs."""

import os
from copy import deepcopy
from datetime import datetime, timezone
from time import monotonic

import requests


def _state():
    # Keep the transport usable in scripts/tests without a Streamlit session.
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        return None
    if get_script_run_ctx(suppress_warning=True) is None:
        return None
    import streamlit as st
    return st.session_state


def _base_url():
    return (os.environ.get('API_BASE_URL') or os.environ.get('NASA_API_URL')
            or 'http://127.0.0.1:8000/api/v1').rstrip('/')


def begin_run():
    """Validate cached private data once per page rerun, never across reruns."""
    state = _state()
    if state is not None:
        state.pop('_api_verified', None)


def clear_data_cache():
    state = _state()
    if state is not None:
        state.pop('_api_data', None)


def close_client():
    state = _state()
    if state is not None:
        session = state.pop('_api_transport', None)
        if session is not None:
            session.close()
        for key in ('_api_data', '_api_identity', '_api_verified'):
            state.pop(key, None)


def _send(method, url, **kwargs):
    state = _state()
    if state is None:
        return requests.request(method, url, **kwargs)
    if '_api_transport' not in state:
        state['_api_transport'] = requests.Session()
    # Headers (including tokens) belong to this request, not the pooled session.
    return state['_api_transport'].request(method, url, **kwargs)


def read(path: str, token: str, params: dict | None = None):
    """Bounded, short-lived GET cache kept exclusively in the current user session."""
    if not (path in ('/body-parts', '/measurements') or path.startswith('/measurements/')):
        return request('GET', path, token, params=params)
    state = _state()
    if state is None:
        return request('GET', path, token, params=params)
    identity = (_base_url(), token)
    if state.get('_api_identity') != identity:
        state['_api_data'] = {}
        state['_api_identity'] = identity
        state.pop('_api_verified', None)
    cache = state.setdefault('_api_data', {})
    key = (path, tuple(sorted((params or {}).items())), datetime.now(timezone.utc).date())
    entry = cache.get(key)
    if entry is not None and monotonic() < entry[0]:
        if state.get('_api_verified') != identity:
            request('GET', '/auth/me', token)
        return deepcopy(entry[1])
    result = request('GET', path, token, params=params)
    cache[key] = (monotonic() + (300 if path == '/body-parts' else 15), deepcopy(result))
    if path == '/measurements/latest' and not params and result.get('date'):
        dated_key = (path, (('date', result['date']),), key[2])
        cache[dated_key] = cache[key]
    while len(cache) > 24:
        cache.pop(next(iter(cache)))
    return result


class ApiError(Exception):
    """A display-safe error with optional validation errors keyed by API field name."""

    def __init__(self, message: str, status: int = 0, fields: dict | None = None):
        super().__init__(message)
        self.status = status
        self.fields = fields or {}


def request(method: str, path: str, token: str | None = None, **kwargs):
    # Keep both existing configuration names working after consolidating the clients.
    base = _base_url()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = _send(method, f"{base}{path}", headers=headers, timeout=(3.05, 15), **kwargs)
    except requests.RequestException:
        raise ApiError("Cannot reach the API. Check that the backend is running.") from None
    if not response.ok:
        if response.status_code == 401:
            clear_data_cache()
            state = _state()
            if state is not None:
                state.pop('_api_verified', None)
        messages = {
            401: "Invalid or expired credentials. Please log in again.",
            409: "Username or email already registered. Try another or log in.",
            422: "The API rejected the request. Check the entered values.",
            429: "Too many attempts. Please try again later.",
        }
        fields = {}
        if response.status_code == 422:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            if isinstance(detail, list):
                for item in detail:
                    if not isinstance(item, dict):
                        continue
                    # Do not echo arbitrary response text, submitted values, or credentials.
                    location = item.get("loc", [])
                    field = next((part for part in reversed(location) if isinstance(part, str)), "request")
                    fields[field] = "Enter a valid value for this field."
            elif detail == "Unknown id_parte; use /api/v1/body-parts":
                fields["id_parte"] = "Choose an available body region."
        raise ApiError(messages.get(response.status_code, "The API could not complete the request. Please try again."),
                       response.status_code, fields)
    if method.upper() not in ('GET', 'HEAD'):
        clear_data_cache()
    if response.status_code == 204:
        return None
    try:
        result = response.json()
    except ValueError:
        raise ApiError("The API returned an invalid response. Please try again.") from None
    if not isinstance(result, (dict, list)):
        raise ApiError("The API returned an invalid response. Please try again.")
    protected = path in ('/auth/me', '/body-parts', '/measurements') or path.startswith('/measurements/')
    if token and protected:
        state = _state()
        if state is not None:
            state['_api_verified'] = (base, token)
    return result


def login(username: str, password: str) -> tuple[str, dict]:
    result = request("POST", "/auth/login", json={"nombre_usuario": username, "password": password})
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise ApiError("The service returned an invalid session. Please try again.")
    return token, request("GET", "/auth/me", token)


def logout(token: str) -> None:
    request("POST", "/auth/logout", token)
