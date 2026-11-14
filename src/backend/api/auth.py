"""Registration, login, current user, and logout endpoints."""

from secrets import token_urlsafe
from time import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.auth.security import SESSION_SECONDS, dummy_hash, hash_password, hash_token, verify_password
from backend.storage.auth import AuthStore, DuplicateUsername

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)


def get_store(request: Request) -> AuthStore:
    return request.app.state.auth_store


Store = Annotated[AuthStore, Depends(get_store)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(store: Store, credentials: Credentials) -> UserResponse:
    if credentials is None:
        raise unauthorized()
    user = store.session_user(hash_token(credentials.credentials), int(time()))
    if user is None:
        raise unauthorized()
    return UserResponse(id=user["id"], username=user["username"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, store: Store) -> UserResponse:
    try:
        user = store.create_user(body.username.lower(), hash_password(body.password.get_secret_value()))
    except DuplicateUsername:
        raise HTTPException(status_code=409, detail="Username already registered") from None
    return UserResponse(**user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, store: Store, response: Response) -> TokenResponse:
    user = store.find_user(body.username.lower())
    valid = verify_password(body.password.get_secret_value(), user["password_hash"] if user else dummy_hash)
    if not valid or user is None:
        raise unauthorized()
    token = token_urlsafe(32)
    now = int(time())
    store.create_session(hash_token(token), user["id"], now + SESSION_SECONDS, now)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=token, expires_in=SESSION_SECONDS)


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[UserResponse, Depends(current_user)]) -> UserResponse:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    store: Store,
    credentials: Credentials,
    user: Annotated[UserResponse, Depends(current_user)],
) -> Response:
    assert credentials is not None  # current_user already verified credentials.
    store.delete_session(hash_token(credentials.credentials))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
