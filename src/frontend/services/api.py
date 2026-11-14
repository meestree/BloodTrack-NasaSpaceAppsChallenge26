"""No database access or shared credential caches in the frontend."""
import os

import requests


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def request(method: str, path: str, token: str | None = None, **kwargs):
    base = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000/api/v1').rstrip('/')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        response = requests.request(method, f'{base}{path}', headers=headers, timeout=15, **kwargs)
    except requests.RequestException:
        raise ApiError('Cannot reach the API. Check that the backend is running.') from None
    if not response.ok:
        messages = {401: 'Your session expired or the credentials are invalid. Please sign in.',
                    422: 'The API rejected the request. Check the entered values.'}
        raise ApiError(messages.get(response.status_code, 'The API could not complete the request.'), response.status_code)
    if response.status_code == 204:
        return None
    try:
        return response.json()
    except ValueError:
        raise ApiError('The API returned an invalid response.') from None
