# BloodTrack API reference

The FastAPI backend exposes a JSON API for account sessions and user-scoped body-region sensor measurements. This reference describes the implementation in `src/backend/`, version **0.1.0**.

**Default base URL:** `http://127.0.0.1:8000/api/v1`

All endpoint paths below are relative to that base. Interactive documentation lives outside the version prefix: [Swagger UI](http://127.0.0.1:8000/docs), [ReDoc](http://127.0.0.1:8000/redoc), and [OpenAPI JSON](http://127.0.0.1:8000/openapi.json). For installation and startup, see [README.md](README.md).

## Contents

- [Conventions](#conventions)
- [Endpoint index](#endpoint-index)
- [Authentication and accounts](#authentication-and-accounts)
- [Health](#health)
- [Body regions](#body-regions)
- [Collect measurements](#collect-measurements)
- [Raw history](#raw-history)
- [Daily summaries](#daily-summaries)
- [Period analytics](#period-analytics)
- [Latest readings](#latest-readings)
- [Movement counts](#movement-counts)
- [Sample statistics](#sample-statistics)
- [Errors](#errors)
- [Try the API](#try-the-api)

## Conventions

- Send JSON request bodies with `Content-Type: application/json`. Field names are case-sensitive; retain Spanish names exactly.
- Protected endpoints require `Authorization: Bearer <access_token>`. All measurement results belong to that token's user. There is no user-ID query parameter for selecting another account.
- Dates use `YYYY-MM-DD`. Submit measurement timestamps as ISO 8601 datetimes with `Z` or a timezone offset. New measurements are normalized to UTC before storage.
- `temperatura` and `caudal` are finite numeric readings. The API specifies neither sensor units nor physiological bounds. Negative readings are not rejected solely for being negative.
- `movimiento` is `0` or `1`: no movement detected / movement detected for that sample.
- Missing data is omitted, not synthesized as zero. An empty result is a successful response with `items: []` (or an empty array for body regions).
- Examples are illustrative. IDs, dates, account age, and numeric values depend on the database and request time. Fetch body-region IDs instead of assuming their values.

### Time windows

History, daily summaries, and period analytics accept `days`: default **7**, minimum **1**, maximum **3,650**. Their window begins at UTC midnight `days - 1` dates before today and ends at request time. Thus `days=1` means today so far, not a rolling 24 hours. The response `from` and `to` values are UTC datetimes. Bounds are inclusive for raw history and period analytics; daily summaries select the corresponding UTC dates.

Movement and sample-statistics endpoints instead accept explicit, inclusive UTC calendar dates. They group a single selected date by hour and a multi-date range by day. Their `from` and `to` values are dates, not datetimes. Ranges must be ordered, end no later than today UTC, and span at most 3,650 calendar dates inclusive.

## Endpoint index

| Method | Path | Authentication | Success |
| --- | --- | --- | --- |
| GET | `/health` | Public | 200 |
| POST | `/auth/register` | Public | 201 |
| POST | `/auth/login` | Public | 200 |
| GET | `/auth/me` | Bearer | 200 |
| POST | `/auth/logout` | Bearer | 204, no body |
| GET | `/body-parts` | Bearer | 200 |
| POST | `/measurements` | Bearer | 201 |
| GET | `/measurements` | Bearer | 200 |
| GET | `/measurements/daily` | Bearer | 200 |
| GET | `/measurements/analytics` | Bearer | 200 |
| GET | `/measurements/latest` | Bearer | 200 |
| GET | `/measurements/movement` | Bearer | 200 |
| GET | `/measurements/statistics` | Bearer | 200 |

Protected endpoints can return 401. Request validation failures return 422. Endpoint-specific errors are described below. There are currently no profile-update, password-reset, measurement-update/delete, or baseline-management endpoints.

## Authentication and accounts

### POST `/auth/register`

Create an account. All fields are required; additional body fields are rejected.

| Field | Type | Validation |
| --- | --- | --- |
| `nombre_usuario` | string | 3–64 ASCII letters, digits, or underscores; pattern `^[a-zA-Z0-9_]{3,64}$`. |
| `password` | string | 12–128 characters. |
| `email` | string | Valid email address, maximum 254 characters. |
| `fecha_nacimiento` | string | Exact `YYYY-MM-DD` date, no later than today UTC. Numeric timestamps are rejected. |

```json
{
  "nombre_usuario": "astronaut_demo",
  "password": "example-only-password",
  "email": "astronaut_demo@example.com",
  "fecha_nacimiento": "1995-05-21"
}
```

**201 Created** returns a public user object:

```json
{
  "id_usuario": 1,
  "nombre_usuario": "astronaut_demo",
  "email": "astronaut_demo@example.com",
  "fecha_nacimiento": "1995-05-21",
  "edad": 31,
  "creado_en": "2026-11-15T10:00:00Z"
}
```

`edad` is calculated by the database view from the birth date and current date. Passwords and hashes are never included. New usernames and email addresses are stored lowercase. Duplicate username or email checks are case-insensitive and return **409** with `"Username or email already registered"`.

Registration does not sign in the user. Call `/auth/login` next.

### POST `/auth/login`

JSON body, not an OAuth form:

```json
{
  "nombre_usuario": "astronaut_demo",
  "password": "example-only-password"
}
```

`nombre_usuario` accepts 1–64 characters; `password` accepts 1–128. Additional fields are rejected. Login looks up usernames case-insensitively; email login is not supported.

**200 OK**:

```json
{
  "access_token": "<opaque-session-token>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The token is an opaque session credential, not a JWT. Use it as returned; do not decode it. Login responses include `Cache-Control: no-store` and `Pragma: no-cache`. Unknown usernames and incorrect passwords return the same **401** response.

Tokens expire one hour after issuance. There is no refresh endpoint; log in again after expiration. Sessions are persisted in SQLite and survive application restarts while valid. The database stores token hashes, not plaintext tokens.

### GET `/auth/me`

Returns **200** with the public user object shown above. No request body or query parameters are required.

### POST `/auth/logout`

Revokes the supplied session token. Returns **204 No Content** with an empty body: do not attempt JSON decoding. Other valid sessions for the account are unaffected. An already revoked, expired, or missing token returns **401**.

## Health

### GET `/health`

Public liveness endpoint. **200 OK**:

```json
{"status": "ok"}
```

This route does not perform a database readiness query or check external services. Normal application startup separately initializes database-backed stores.

## Body regions

### GET `/body-parts`

Returns the configured region catalog, ordered by `id_parte`. **200 OK**, a top-level array:

```json
[
  {"id_parte": 1, "nombre": "Cuello"},
  {"id_parte": 2, "nombre": "Brazo izquierdo"}
]
```

Each item has an integer `id_parte` and string `nombre`. The supplied schema supports `Cuello`, `Brazo izquierdo`, `Brazo derecho`, `Pierna izquierda`, and `Pierna derecha`; the actual returned IDs and available rows come from the database. No regions configured returns `[]`.

## Collect measurements

### POST `/measurements`

Submit a batch of **1–1,000** samples in a `measurements` array. All item fields are required; extra fields at either level are rejected.

| Field | Type | Validation / meaning |
| --- | --- | --- |
| `id_parte` | integer | Strict positive integer, must exist in `/body-parts`; strings and booleans are rejected. |
| `timestamp` | timezone-aware datetime | Cannot be in the future; normalized to UTC. |
| `temperatura` | number | Finite; no declared unit or physiological range. |
| `caudal` | number | Finite; no declared unit or physiological range. |
| `movimiento` | 0 or 1 | Movement flag for the sample. |

```json
{
  "measurements": [
    {
      "id_parte": 1,
      "timestamp": "2020-01-02T10:00:00Z",
      "temperatura": 36.0,
      "caudal": 750.0,
      "movimiento": 1
    }
  ]
}
```

**201 Created**:

```json
{"created": 1, "ids": [101]}
```

`ids` contains the inserted `id_registro` values in submission order. The authenticated user is assigned server-side: **do not submit `id_usuario`**.

Batch insertion and affected daily-summary updates are atomic. An unknown part returns **422** with `"Unknown id_parte; use /api/v1/body-parts"` and inserts none of the batch. Invalid input also returns 422. Backdated samples update their corresponding daily summaries.

There is no idempotency or duplicate suppression. Retrying a successful submission creates new rows. If a connection fails before the client receives a response, inspect history before retrying when duplicates matter.

## Raw history

### GET `/measurements`

| Query | Type | Default | Constraints |
| --- | --- | --- | --- |
| `days` | integer | 7 | 1–3,650 UTC dates including today. |
| `id_parte` | integer | omitted | Positive; filters by region. |
| `limit` | integer | 100 | 1–1,000. |
| `offset` | integer | 0 | At least 0. |

Example: `/measurements?days=30&id_parte=1&limit=25&offset=0`.

**200 OK**:

```json
{
  "from": "2020-01-01T00:00:00Z",
  "to": "2020-01-02T12:00:00Z",
  "total": 1,
  "limit": 100,
  "offset": 0,
  "items": [
    {
      "id_registro": 101,
      "id_usuario": 1,
      "id_parte": 1,
      "timestamp": "2020-01-02T10:00:00.000000Z",
      "temperatura": 36.0,
      "caudal": 750.0,
      "movimiento": 1
    }
  ]
}
```

This illustrates `days=2` on January 2, 2020. Rows are ordered by timestamp descending, then `id_registro` descending to break ties. `total` counts all matching samples before pagination. Advance `offset` by `limit`; no more rows remain when `offset + len(items) >= total`. Each request computes a new window, so pagination is not a fixed snapshot.

An unknown positive region ID returns an empty result rather than an unknown-part error. An offset past the result set returns `items: []` while retaining the matching `total`.

## Daily summaries

### GET `/measurements/daily`

Accepts `days` and optional positive `id_parte`, with the same defaults and constraints as history. No pagination.

**200 OK**:

```json
{
  "from": "2020-01-01T00:00:00Z",
  "to": "2020-01-02T12:00:00Z",
  "items": [
    {
      "id_usuario": 1,
      "id_parte": 1,
      "fecha": "2020-01-02",
      "muestras": 1,
      "temperatura_media": 36.0,
      "caudal_media": 750.0,
      "movimiento_unos": 1
    }
  ]
}
```

One row per user, region, and UTC date, ordered by `fecha` then `id_parte` ascending. `muestras` is the sample count; the means are arithmetic means of those samples; `movimiento_unos` counts samples marked `1`. Unsampled dates and regions are omitted.

These summaries are persisted, refreshed for affected groups during API collection, and fully rebuilt from `registros` at application startup. Direct out-of-band database edits do not automatically refresh persisted summaries while the server is running.

## Period analytics

### GET `/measurements/analytics`

Accepts `days` and optional positive `id_parte`, as above. No pagination. Returns one row per sampled region, ordered by `id_parte`.

**200 OK**:

```json
{
  "from": "2020-01-01T00:00:00Z",
  "to": "2020-01-02T12:00:00Z",
  "days": 2,
  "items": [
    {
      "id_parte": 1,
      "muestras": 1,
      "temperatura_media": 36.0,
      "temperatura_min": 36.0,
      "temperatura_max": 36.0,
      "caudal_media": 750.0,
      "caudal_min": 750.0,
      "caudal_max": 750.0,
      "movimiento_unos": 1,
      "movimiento_fraccion": 1.0,
      "dias_con_datos": 1,
      "dias_sin_datos": 1,
      "cobertura_dias_fraccion": 0.5
    }
  ]
}
```

| Field(s) | Meaning |
| --- | --- |
| `muestras` | Number of samples in the requested window. |
| `temperatura_media`, `caudal_media` | Arithmetic means across all samples, not unweighted means of daily means. |
| `*_min`, `*_max` | Minimum and maximum observed values. |
| `movimiento_unos` | Number of movement-marked samples. |
| `movimiento_fraccion` | `movimiento_unos / muestras`, a fraction from 0 to 1. |
| `dias_con_datos` | Distinct UTC dates with at least one sample. |
| `dias_sin_datos` | `days - dias_con_datos`. |
| `cobertura_dias_fraccion` | `dias_con_datos / days`, a fraction from 0 to 1. |

A region with no samples is omitted entirely; it is not returned with zero means or zero coverage.

## Latest readings

### GET `/measurements/latest`

Optional query: `date=YYYY-MM-DD`.

With a date, returns the most recent sample for each region on that UTC date. Without it, selects the authenticated user's latest recorded UTC day; this need not be today. Ties use the highest `id_registro`. Rows are ordered by `id_parte`.

**200 OK**:

```json
{
  "date": "2020-01-02",
  "items": [
    {
      "id_registro": 101,
      "id_usuario": 1,
      "id_parte": 1,
      "nombre": "Cuello",
      "timestamp": "2020-01-02T10:00:00.000000Z",
      "temperatura": 36.0,
      "caudal": 750.0,
      "movimiento": 1
    }
  ]
}
```

No readings on an explicit date returns `{"date":"2020-01-03","items":[]}`. No readings at all with the date omitted returns `{"date":null,"items":[]}`. An invalid date returns 422. Unlike movement/statistics, this endpoint does not reject a well-formed future date; it normally returns an empty result. There is no `id_parte` filter or pagination.

## Movement counts

### GET `/measurements/movement`

| Query | Type | Required | Meaning |
| --- | --- | --- | --- |
| `start_date` | date | Yes | First UTC date, inclusive. |
| `end_date` | date | Yes | Last UTC date, inclusive. |
| `id_parte` | positive integer | No | Filter to one region; omitted combines samples from all regions. |

The date-range rules in [Time windows](#time-windows) apply. **200 OK** for a single date:

```json
{
  "from": "2020-01-02",
  "to": "2020-01-02",
  "granularity": "hour",
  "items": [
    {"periodo": "2020-01-02T10:00:00Z", "muestras": 2, "movimiento_unos": 1}
  ]
}
```

For multiple dates, `granularity` is `"day"` and `periodo` is `"2020-01-02"`. Rows are ordered by period ascending. Hours/days without samples are omitted. A sampled period with no movement still appears with `movimiento_unos: 0`.

Counts measure movement-marked **samples**, not distinct events or duration. When regions are combined, readings from each region contribute separately.

## Sample statistics

### GET `/measurements/statistics`

| Query | Type | Required / default | Meaning |
| --- | --- | --- | --- |
| `start_date` | date | Required | First UTC date, inclusive. |
| `end_date` | date | Required | Last UTC date, inclusive. |
| `metric` | string | `temperatura` | Exactly `temperatura` or `caudal`. |

The same explicit date-range rules apply. This endpoint has no region filter: it returns all sampled regions, grouped separately by region and period, ordered by `id_parte` then `periodo`.

**200 OK**:

```json
{
  "from": "2020-01-02",
  "to": "2020-01-02",
  "metric": "temperatura",
  "granularity": "hour",
  "items": [
    {
      "id_parte": 1,
      "nombre": "Cuello",
      "periodo": "2020-01-02T10:00:00Z",
      "muestras": 2,
      "media": 37.0,
      "minimo": 36.0,
      "maximo": 38.0,
      "desviacion_estandar": 1.4142135623730951
    }
  ]
}
```

Single-date requests use hourly periods; multi-date requests use daily periods. `media`, `minimo`, and `maximo` describe the selected metric. `desviacion_estandar` is the **sample** standard deviation, `sqrt(sum((x - mean)^2) / (n - 1))`, computed with Welford's algorithm. For one sample it is **null**, not zero. Groups without samples are omitted. The API returns no color statuses, reference thresholds, or confidence intervals.

## Errors

Errors use a top-level `detail` field. Clients should handle both strings and validation arrays. Do not log passwords or access tokens.

### Authentication: 401

```json
{"detail": "Invalid or expired credentials"}
```

Includes `WWW-Authenticate: Bearer`. Used for invalid login credentials and missing, malformed, expired, or revoked bearer credentials. Clear the client's session and return to login when an authenticated request receives 401.

### Duplicate account: 409

```json
{"detail": "Username or email already registered"}
```

### Request validation: 422

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "measurements", 0, "caudal"],
      "msg": "Field required"
    }
  ]
}
```

`loc` identifies the source (`body` or `query`), field path, and array index when applicable. Map these paths to the relevant inputs. The custom validation handler returns only `type`, `loc`, and `msg`; it strips submitted values and validation context to avoid echoing secrets. Exact messages/types depend on the validation failure and installed dependency versions.

Business validation can instead return a string:

| Condition | `detail` |
| --- | --- |
| Unknown region during collection | `Unknown id_parte; use /api/v1/body-parts` |
| Movement date range reversed | `End date must be on or after start date` |
| Movement end date in future | `Dates cannot be in the future` |
| Statistics reversed/future range | `Select an ordered date range without future dates` |
| Movement/statistics range over 3,650 inclusive dates | `Select at most 3650 days` |

Infrastructure failures are not guaranteed to use the validation envelope. Handle unavailable services and unexpected server responses separately from field errors. The backend does not currently implement application-level rate limiting; clients should not rely on a documented 429 policy.

## Try the API

The following Bash example uses `curl` and Python, against a running local API. The credentials are fictional demonstration values; choose your own for local use. Re-running registration with the same account returns 409.

```bash
API_URL=http://127.0.0.1:8000/api/v1

curl --fail-with-body -sS "$API_URL/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"nombre_usuario":"astronaut_demo","password":"example-only-password","email":"astronaut_demo@example.com","fecha_nacimiento":"1995-05-21"}'

# Keep the returned token in a shell variable rather than printing it.
TOKEN=$(curl --fail-with-body -sS "$API_URL/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"nombre_usuario":"astronaut_demo","password":"example-only-password"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl --fail-with-body -sS "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN"

curl --fail-with-body -sS "$API_URL/body-parts" \
  -H "Authorization: Bearer $TOKEN"
```

Choose a returned `id_parte` before submitting a measurement. For example, **if region 1 exists**:

```bash
curl --fail-with-body -sS "$API_URL/measurements" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"measurements":[{"id_parte":1,"timestamp":"2020-01-02T10:00:00Z","temperatura":36.0,"caudal":750.0,"movimiento":1}]}'

# Explicit historical queries find this backdated example regardless of today's rolling window.
curl --fail-with-body -sS "$API_URL/measurements/latest?date=2020-01-02" \
  -H "Authorization: Bearer $TOKEN"

curl --fail-with-body -sS "$API_URL/measurements/statistics?start_date=2020-01-02&end_date=2020-01-02&metric=temperatura" \
  -H "Authorization: Bearer $TOKEN"

# Recent history can be empty because the example above is backdated.
curl --fail-with-body -sS "$API_URL/measurements?days=7&limit=25&offset=0" \
  -H "Authorization: Bearer $TOKEN"

curl --fail-with-body -sS -X POST "$API_URL/auth/logout" \
  -H "Authorization: Bearer $TOKEN"
unset TOKEN
```

For Postman or Swagger UI, register/login using JSON, then apply the returned token using Bearer authentication. Supply the token value alone in a Bearer-token input; those tools add the `Bearer` prefix. Never save live credentials in shared collections.
