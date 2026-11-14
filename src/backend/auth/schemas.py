"""Authentication requests and public responses."""

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_usuario: str = Field(pattern=r"^[a-zA-Z0-9_]{3,64}$")
    password: SecretStr = Field(min_length=12, max_length=128)
    email: EmailStr = Field(max_length=254)
    fecha_nacimiento: date

    @field_validator("fecha_nacimiento", mode="before")
    @classmethod
    def validate_birth_date(cls, value: object) -> date:
        # Accept calendar dates only, never numeric Unix timestamps.
        if not isinstance(value, str):
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError("Use a calendar date in YYYY-MM-DD format") from None
        if value != parsed.isoformat():
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        if parsed > datetime.now(timezone.utc).date():
            raise ValueError("Birth date cannot be in the future")
        return parsed


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_usuario: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id_usuario: int
    nombre_usuario: str
    email: str
    fecha_nacimiento: date
    edad: int
    creado_en: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
