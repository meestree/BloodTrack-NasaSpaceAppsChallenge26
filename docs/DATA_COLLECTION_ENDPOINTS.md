# Data collection API

Start with `./start_api.sh`. Base URL: `http://127.0.0.1:8000/api/v1`.
Every endpoint below requires `Authorization: Bearer <access_token>` from login.
Requests cannot select another user: ownership comes from the token.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/body-parts` | Available `id_parte` and `nombre` values |
| POST | `/measurements` | Store a batch of raw readings |
| GET | `/measurements?days=7` | Paginated history |
| GET | `/measurements/daily?days=7` | Stored daily arithmetic means per body region |
| GET | `/measurements/analytics?days=7` | Period means, ranges, movement fraction, and day coverage |

## Collection

In Postman select Body → raw → JSON and `Content-Type: application/json`.
Fetch `/body-parts` first; use the actual IDs it returns.

Example (replace the timestamp with the actual measurement time):

```json
{
  "measurements": [
    {
      "id_parte": 1,
      "timestamp": "2026-11-14T12:00:00Z",
      "temperatura": 32.5,
      "caudal": 10.2,
      "movimiento": 1
    }
  ]
}
```

Each batch contains 1–1000 readings. Regions can arrive separately or together.
Timestamps must include a timezone and cannot be in the future; storage uses UTC.
Temperature is in Celsius. Flow values are retained in the device's unit without
conversion; the unit is currently unspecified. `movimiento` is 0 or 1, where 1
means movement detected. Numeric values must be finite. No physiological ranges
are imposed yet. Unknown JSON fields, including `id_usuario`, are rejected.

Success: 201, `{"created": 1, "ids": [1]}`. Each submission appends readings;
retrying a successful request creates additional samples. Batches are atomic:
an unknown body part returns 422 and none of the batch is stored.

## Last X days and pagination

`days` defaults to 7 and accepts 1–3650. It counts UTC calendar days, including
today: `days=1` means today from midnight until the request time, rather than a
rolling 24-hour period. Responses include `from` and `to` timestamps.

All history/summary endpoints accept optional `id_parte` to select a region.
Raw history also accepts `limit` (1–1000, default 100) and `offset` (default 0).
Rows are newest first, with `id_registro` breaking timestamp ties.

Example: `/measurements?days=30&id_parte=1&limit=100&offset=0`.
History returns `total`, `limit`, `offset`, and `items`. Each item contains
`id_registro`, `id_usuario`, `id_parte`, `timestamp`, `temperatura`, `caudal`,
and `movimiento`. Empty results have `total: 0` and `items: []`.

## Stored arithmetic means

`/measurements/daily` returns `items`, ordered by date and region. Each item has:

- `id_usuario`, `id_parte`, `fecha` (UTC date).
- `muestras`: number of samples contributing to both means.
- `temperatura_media`, `caudal_media`: sum of values divided by sample count.
- `movimiento_unos`: number of readings with movement detected.

These summaries are persisted in the added `resumenes_diarios` table. Raw
readings remain in `registros`. Ingestion updates the affected daily summaries
in the same transaction, including readings submitted for earlier days. Existing
records are backfilled on startup. Direct database edits/imports require a server
restart to refresh stored summaries. Baseline tables are not modified.

Means are per region and sample-weighted, not time-weighted. A day with more
samples contributes more to a period mean. Missing days are not treated as zero.
Repeated uploads are counted as additional samples.

## Analytics useful for longer histories

`/measurements/analytics` returns `days`, `from`, `to`, and `items`, one item per
region with data. Calculations use all matching raw samples, not just one page:

- `muestras`: total readings.
- `temperatura_media`, `temperatura_min`, `temperatura_max`.
- `caudal_media`, `caudal_min`, `caudal_max`.
- `movimiento_unos`, `movimiento_fraccion` (movement readings / all readings).
- `dias_con_datos`, `dias_sin_datos`, `cobertura_dias_fraccion`.

Coverage means days with at least one sample divided by requested days. It does
not measure continuous sensor availability. Regions with no samples are omitted;
combine with `/body-parts` to show these as no data in the frontend. Movement
fraction describes samples with movement, not time spent moving.

Useful follow-up analyses include hourly patterns, baseline-relative trends,
variability, cross-signal correlations, and sampling gaps. These are not yet
implemented. They require agreed units, a sampling cadence, and enough data to
interpret reliably. Descriptive summaries here do not infer clinical conditions.

## Errors

- 401: missing, invalid, revoked, or expired bearer token.
- 422: invalid measurement, unknown body part on ingestion, or invalid query.
- Invalid bodies use the existing `detail` validation response format.

No measurement update, delete, latest-reading, or baseline-management endpoints
are included in this iteration.
