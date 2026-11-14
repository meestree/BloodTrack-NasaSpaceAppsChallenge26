"""Authentication API calls run on the Streamlit server, never in browser URLs."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ApiError(Exception):
    """An error safe to display without exposing response bodies or credentials."""


def request(method: str, path: str, payload: dict | None = None, token: str | None = None) -> dict:
    base_url = os.environ.get("NASA_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urlopen(Request(f"{base_url}{path}", data=body, headers=headers, method=method), timeout=10) as response:
            content = response.read()
            return json.loads(content) if content else {}
    except HTTPError as error:
        messages = {401: "Invalid or expired credentials. Please log in again.", 429: "Too many attempts. Please try again later."}
        raise ApiError(messages.get(error.code, "The service could not complete your request. Please try again.")) from None
    except (URLError, OSError):
        raise ApiError("Cannot reach the service. Please try again shortly.") from None
    except (ValueError, UnicodeError):
        raise ApiError("The service returned an unexpected response. Please try again.") from None


def login(username: str, password: str) -> tuple[str, dict]:
    result = request("POST", "/auth/login", {"nombre_usuario": username, "password": password})
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise ApiError("The service returned an invalid session. Please try again.")
    return token, request("GET", "/auth/me", token=token)


def logout(token: str) -> None:
    request("POST", "/auth/logout", token=token)
