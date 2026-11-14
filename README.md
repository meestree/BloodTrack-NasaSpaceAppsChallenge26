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

Only the health endpoint is implemented. Measurement ingestion, storage,
baseline calculations, authentication, and the dashboard are future work.
No physiological formulas or blood-volume estimates are implemented.
