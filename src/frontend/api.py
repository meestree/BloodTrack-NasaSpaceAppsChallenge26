"""One server-side API client for every page; credentials never enter browser URLs."""

import os

import requests


class ApiError(Exception):
    """A display-safe error with optional validation errors keyed by API field name."""

    def __init__(self, message: str, status: int = 0, fields: dict | None = None):
        super().__init__(message)
        self.status = status
        self.fields = fields or {}


def request(method: str, path: str, token: str | None = None, **kwargs):
    # Keep both existing configuration names working after consolidating the clients.
    base = (os.environ.get("API_BASE_URL") or os.environ.get("NASA_API_URL")
            or "http://127.0.0.1:8000/api/v1").rstrip("/")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, f"{base}{path}", headers=headers, timeout=15, **kwargs)
    except requests.RequestException:
        raise ApiError("Cannot reach the API. Check that the backend is running.") from None
    if not response.ok:
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
    if response.status_code == 204:
        return None
    try:
        result = response.json()
    except ValueError:
        raise ApiError("The API returned an invalid response. Please try again.") from None
    if not isinstance(result, (dict, list)):
        raise ApiError("The API returned an invalid response. Please try again.")
    return result


def login(username: str, password: str) -> tuple[str, dict]:
    result = request("POST", "/auth/login", json={"nombre_usuario": username, "password": password})
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise ApiError("The service returned an invalid session. Please try again.")
    return token, request("GET", "/auth/me", token)


def logout(token: str) -> None:
    request("POST", "/auth/logout", token)
