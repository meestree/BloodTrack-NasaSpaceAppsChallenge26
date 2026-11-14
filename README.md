# NASA Space Apps backend

Python API skeleton for five-region physiological sensor data. Development is
on the `backend` branch; the Streamlit frontend belongs on `frontend`.

## Setup

Use Python 3.11 or newer with pip and venv installed:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m uvicorn backend.main:app --reload
```

Health: `http://127.0.0.1:8000/api/v1/health`.
Interactive API reference: `http://127.0.0.1:8000/docs`.
Run checks with `python -m pytest`.

## Structure

```text
src/backend/
  main.py          # Creates the FastAPI application
  api/             # HTTP endpoints, status codes, response models
  ingestion/       # JSON sensor contracts and validation
  processing/      # Reserved for baselines and trends
  storage/         # Reserved for measurement history
  simulation/      # Reserved for synthetic sensor generators
tests/             # API and payload validation checks
```

An API receives an HTTP request, validates its input, calls application logic,
and returns a response. Routes belong in `api/`; processing and persistence
remain separate so the dashboard can consume the same backend behavior.
The router organization follows the
[FastAPI multiple-file guide](https://fastapi.tiangolo.com/tutorial/bigger-applications/).

## Initial sensor contract

`ingestion/schemas.py` defines one timezone-aware timestamp and all five regions
per payload. Each region requires positive, finite `impedance_ohm`. The four
extremities also require `skin_temperature_c`. Optional
`muscle_oxygen_saturation_pct` accepts a percentage or null. The required `source`
field distinguishes `real` and `simulated` data. Unknown fields are rejected.
This nested JSON shape is an initial API design; confirm it against the device
firmware before implementing ingestion.

The health and authentication endpoints are implemented. Measurement ingestion,
measurement storage, baseline calculations, and the dashboard are future work.
No physiological formulas or blood-volume estimates are implemented.

## Authentication

Install the updated dependencies with `python -m pip install -e '.[dev]'`.
The supplied `data/astronautas.db` must exist and contain `usuarios` and
`vista_usuarios`. Startup validates that schema and creates only `auth_sessions`,
linked to `usuarios.id_usuario`. It does not create a second users table or
replace the supplied schema. Tests use temporary databases built from a schema
snapshot with no personal data.

| Endpoint | JSON request / authorization | Result |
| --- | --- | --- |
| `POST /api/v1/auth/register` | `nombre_usuario`, `password`, `email`, `fecha_nacimiento` | Public user profile (201) |
| `POST /api/v1/auth/login` | `nombre_usuario`, `password` | `access_token`, `token_type`, `expires_in` |
| `GET /api/v1/auth/me` | `Authorization: Bearer <access_token>` | Public user profile |
| `POST /api/v1/auth/logout` | `Authorization: Bearer <access_token>` | Revokes the current session (204) |

Usernames are case-insensitive, 3–64 ASCII letters, digits, or underscores.
Emails are validated and normalized to lowercase; duplicate usernames or emails
return 409. Dates of birth must be valid, non-future `YYYY-MM-DD` strings.
Profiles expose `id_usuario`, `nombre_usuario`, `email`, `fecha_nacimiento`,
`edad`, and `creado_en`, using `vista_usuarios` for the calculated age.
Registration requires passwords of 12–128 characters. The server hashes
passwords with salted Argon2id; clients send the original password over HTTPS.
Neither passwords nor hashes are returned by the API, including validation errors.

Sessions last one hour and survive restarts. Only SHA-256 hashes of random
session tokens are stored; the original token is returned once at login.
The frontend should keep it out of logs and send it in the authorization header.
New protected routes must depend on `backend.api.auth.current_user`.

Registration is currently open. Rate limiting, account recovery, email
verification, and role-based authorization are not implemented. Use HTTPS and
add login rate limiting before exposing this prototype publicly. Keep the live
database out of Git; share schema through the initialization code instead.

### Postman JSON bodies

Register with `POST http://127.0.0.1:8000/api/v1/auth/register`:

```json
{
  "nombre_usuario": "astronaut",
  "password": "example-password-change-me",
  "email": "astronaut@example.com",
  "fecha_nacimiento": "1995-05-21"
}
```

Log in with `POST http://127.0.0.1:8000/api/v1/auth/login`:

```json
{
  "nombre_usuario": "astronaut",
  "password": "example-password-change-me"
}
```

Use Body → raw → JSON in Postman. For `/me` and `/logout`, use Authorization →
Bearer Token and paste the returned `access_token`.
