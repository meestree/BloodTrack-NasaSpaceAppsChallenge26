# NASA Space Apps API

API version: `0.1.0`. All application endpoints use the `/api/v1` prefix.
Requests and responses use JSON, except the empty logout response. Field names
are case-sensitive and retain the Spanish names used by the backend.

## Running locally

Requires Python 3.11 or later and the existing `data/astronautas.db` database
with the supplied application schema. The server does not create a replacement
database if it is missing.

From the repository root, using your Python environment:

```sh
python -m pip install -e .
uvicorn backend.main:app --reload
```

The default local base URL is `http://127.0.0.1:8000/api/v1`.
FastAPI also exposes Swagger UI at `/docs`, ReDoc at `/redoc`, and the OpenAPI
schema at `/openapi.json` (outside the versioned prefix). Measurement response
fields are described below because their full shapes are not declared in OpenAPI.

## Endpoints

| Method | Path (after `/api/v1`) | Authentication | Success |
| --- | --- | --- | --- |
| GET | `/health` | Public | 200 |
| POST | `/auth/register` | Public | 201 |
| POST | `/auth/login` | Public | 200 |
| GET | `/auth/me` | Bearer token | 200 |
| POST | `/auth/logout` | Bearer token | 204 |
| GET | `/body-parts` | Bearer token | 200 |
| POST | `/measurements` | Bearer token | 201 |
| GET | `/measurements` | Bearer token | 200 |
| GET | `/measurements/daily` | Bearer token | 200 |
| GET | `/measurements/analytics` | Bearer token | 200 |

## Authentication

Register an account, then log in to obtain an opaque session token. Send it on
protected requests using `Authorization: Bearer <access_token>`. Tokens expire
after 3,600 seconds. Logging out revokes the token used for that request.
Measurement access is scoped to the authenticated user; clients do not submit
an `id_usuario` to select an owner.

### POST `/auth/register`

```json
{
  "nombre_usuario": "researcher_01",
  "password": "example-password-123",
  "email": "researcher@example.com",
  "fecha_nacimiento": "1990-01-15"
}
```

| Field | Rules |
| --- | --- |
| `nombre_usuario` | 3–64 ASCII letters, digits, or underscores |
| `password` | 12–128 characters |
| `email` | Valid email address, maximum 254 characters |
| `fecha_nacimiento` | Calendar date in `YYYY-MM-DD`; cannot be in the future (UTC) |

All fields are required. Extra fields are rejected. Usernames and email addresses
are stored in lowercase; duplicate checks are case-insensitive. Registration
returns a user object with HTTP 201, but does not create a session.

Example user object (also returned by `/auth/me`; values are illustrative):

```json
{
  "id_usuario": 1,
  "nombre_usuario": "researcher_01",
  "email": "researcher@example.com",
  "fecha_nacimiento": "1990-01-15",
  "edad": 36,
  "creado_en": "2026-11-14T10:00:00"
}
```

`edad` comes from the database user view. `creado_en` is the account creation
datetime. Passwords and password hashes are never returned.

### POST `/auth/login`

```json
{
  "nombre_usuario": "researcher_01",
  "password": "example-password-123"
}
```

The username is case-insensitive and must contain 1–64 characters. The password
must contain 1–128 characters. Both fields are required; extra fields are rejected.

HTTP 200 response:

```json
{
  "access_token": "<opaque-session-token>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The response includes `Cache-Control: no-store` and `Pragma: no-cache`.

### GET `/auth/me`

Returns the authenticated user's user object with HTTP 200.

### POST `/auth/logout`

Requires a valid bearer token and no request body. Returns HTTP 204 with no
response body. Reusing the revoked token returns HTTP 401.

## Health and body parts

### GET `/health`

Returns HTTP 200 with `{"status":"ok"}`. This is a liveness check, not a database
or external-service readiness check.

### GET `/body-parts`

Returns the configured body parts, ordered by `id_parte`. Use this endpoint to
discover valid measurement identifiers; the example values are illustrative.

```json
[
  {"id_parte": 1, "nombre": "Cuello"},
  {"id_parte": 2, "nombre": "Brazo izquierdo"}
]
```

## Collecting measurements

### POST `/measurements`

Send an object containing a `measurements` array with 1–1,000 items:

```json
{
  "measurements": [
    {
      "id_parte": 1,
      "timestamp": "2026-01-01T12:00:00Z",
      "temperatura": 32.0,
      "caudal": 15.0,
      "movimiento": 1
    }
  ]
}
```

| Item field | Rules |
| --- | --- |
| `id_parte` | Positive integer from `/body-parts`; strings and booleans are rejected |
| `timestamp` | Timezone-aware datetime, no later than the current time; normalized to UTC |
| `temperatura` | Finite number |
| `caudal` | Finite number |
| `movimiento` | Binary value: `0` or `1` |

All item fields are required. Extra fields in the batch or individual items are
rejected. The API does not define units or physical range limits for
`temperatura` and `caudal`. Send consistent sensor units.

HTTP 201 response:

```json
{"created": 1, "ids": [123]}
```

`ids` contains the created measurement identifiers in input order. Collection is
atomic: an unknown body part rejects the entire batch. Backdated measurements
are accepted and update the affected daily summaries. There is no deduplication
key; resubmitting a batch creates additional records.

## History and aggregation

All three GET endpoints below accept these optional query parameters:

| Parameter | Default | Rules |
| --- | --- | --- |
| `days` | `7` | Integer from 1 to 3,650 |
| `id_parte` | All parts | Positive integer body-part filter |

The window starts at UTC midnight `days - 1` calendar days before today and ends
at the current UTC time. Thus, `days=1` means today so far. Responses include
`from` and `to` datetime strings. History and analytics include both boundaries.
An unmatched positive body-part filter returns an empty `items` array.

### GET `/measurements`

Also accepts `limit` (default `100`, range 1–1,000) and `offset` (default `0`,
minimum `0`). Results are ordered by timestamp descending, then `id_registro`
descending. `total` counts all matching records before pagination.

Example response:

```json
{
  "from": "2026-01-01T00:00:00Z",
  "to": "2026-01-01T13:00:00Z",
  "total": 1,
  "limit": 100,
  "offset": 0,
  "items": [
    {
      "id_registro": 123,
      "id_usuario": 1,
      "id_parte": 1,
      "timestamp": "2026-01-01T12:00:00.000000Z",
      "temperatura": 32.0,
      "caudal": 15.0,
      "movimiento": 1
    }
  ]
}
```

### GET `/measurements/daily`

Returns `{"from": "<UTC datetime>", "to": "<UTC datetime>", "items": [...]}`.
Items are persisted summaries grouped by UTC calendar date and body part,
ordered by `fecha` ascending, then `id_parte` ascending:

```json
{
  "id_usuario": 1,
  "id_parte": 1,
  "fecha": "2026-01-01",
  "muestras": 2,
  "temperatura_media": 32.0,
  "caudal_media": 15.0,
  "movimiento_unos": 1
}
```

`muestras` is the sample count, the `*_media` fields are arithmetic means, and
`movimiento_unos` counts samples whose movement value is 1. Daily summaries
select whole dates within the window, including today's partial date. Missing
dates are omitted rather than filled with zeros. This endpoint has no pagination.

### GET `/measurements/analytics`

Returns `{"from": "<UTC datetime>", "to": "<UTC datetime>", "days": 7, "items": [...]}`.
Items summarize the selected period per body part, ordered by `id_parte`:

```json
{
  "id_parte": 1,
  "muestras": 2,
  "temperatura_media": 32.0,
  "temperatura_min": 30.0,
  "temperatura_max": 34.0,
  "caudal_media": 15.0,
  "caudal_min": 10.0,
  "caudal_max": 20.0,
  "movimiento_unos": 1,
  "movimiento_fraccion": 0.5,
  "dias_con_datos": 1,
  "dias_sin_datos": 6,
  "cobertura_dias_fraccion": 0.14285714285714285
}
```

Period means are calculated across raw samples, so days with more samples have
more weight. `movimiento_fraccion` is `movimiento_unos / muestras`.
`dias_con_datos` counts distinct UTC dates with samples; `dias_sin_datos` is
`days - dias_con_datos`; `cobertura_dias_fraccion` is `dias_con_datos / days`.
Parts without samples are omitted. This endpoint has no pagination.

## Errors

| Status | Meaning | Response `detail` |
| --- | --- | --- |
| 401 | Missing, invalid, expired, or revoked token; invalid login | `"Invalid or expired credentials"` |
| 409 | Duplicate username or email during registration | `"Username or email already registered"` |
| 422 | Unknown body part during collection | `"Unknown id_parte; use /api/v1/body-parts"` |
| 422 | Invalid request body or query parameters | Array of validation errors |

HTTP 401 responses include `WWW-Authenticate: Bearer`. String errors use an
object such as `{"detail":"Invalid or expired credentials"}`. Request validation
errors include only `type`, `loc`, and `msg`, without echoing submitted values:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "days"],
      "msg": "Input should be greater than or equal to 1"
    }
  ]
}
```

## Example authenticated request

Replace the placeholder with the token returned by `/auth/login`:

```sh
curl 'http://127.0.0.1:8000/api/v1/measurements?days=7&limit=100' \
  -H 'Authorization: Bearer <access_token>'
```
