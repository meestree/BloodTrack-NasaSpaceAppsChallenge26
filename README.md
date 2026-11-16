# BloodTrack · NASA Space Apps
![Logo del proyecto](src/frontend/assets/logo.png)
This is our project for the hackaton "NASA Space Apps". We had 48 hours to solve the challenge "Health monitoring system for astronauts". So we decided to develop BloodTrack.

BloodTrack is a body-region sensor dashboard by **Space Dracula** for exploring measurements in the context of microgravity research. It combines a Streamlit interface, a FastAPI backend, and a supplied SQLite sample database.

Users can register, sign in, record measurements, inspect their history, and explore temperature, microcirculation, movement-marked samples, and statistical summaries. The frontend communicates with the API; it never reads SQLite directly.

- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Using the application](#using-the-application)
- [Project structure](#project-structure)
- [Database behavior](#database-behavior)
- [Development and tests](#development-and-tests)
- [Troubleshooting](#troubleshooting)
- [API reference](API.md)

## Getting started

### Requirements

- Python **3.11 or newer** and `pip`.
- A checkout of this repository, including `data/astronautas.db`.
- Two terminal sessions: one for FastAPI and one for Streamlit.

Run the following commands from the repository root. An editable installation is recommended: the frontend uses fonts and body-map images from the checkout.

### 1. Create an environment and install

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[frontend,dev]'
```

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[frontend,dev]"
```

The `frontend` extra installs Streamlit, Requests, pandas, and Altair. The `dev` extra installs pytest and HTTPX. For an API-only installation, use `python -m pip install -e .`.

Use the `pyproject.toml` installation above. The current root `requirements.txt` includes `src/frontend/requirements.txt`, which is removed in the current working tree; that installation route will fail until the reference is updated.

### 2. Start the backend

In the first terminal, with the environment activated:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `.\.venv\Scripts\python.exe` in place of `python` if the environment is not activated.

The repository also provides launchers that locate an interpreter and pass additional arguments to Uvicorn:

| Platform | Command |
| --- | --- |
| Linux / macOS | `bash start_api.sh --reload` |
| Windows PowerShell | `.\start_api.ps1 --reload` |
| Windows Command Prompt | `start_api.cmd --reload` |

The shell launcher expects `.venv/bin/python`. The PowerShell launcher checks the local virtual environment and supported Conda locations, and accepts `-PythonExecutable` to select an interpreter explicitly.

Verify the API:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response: `{"status":"ok"}`.

### 3. Start the frontend

In a second terminal using the same environment:

```bash
python -m streamlit run src/frontend/app.py
```

Open the local URL printed by Streamlit, normally **http://localhost:8501**. Register an account and then log in; registration does not create a session automatically.

### Local addresses

| Service | Default URL |
| --- | --- |
| Frontend | http://localhost:8501 |
| API base | http://127.0.0.1:8000/api/v1 |
| Swagger UI | http://127.0.0.1:8000/docs |
| ReDoc | http://127.0.0.1:8000/redoc |
| OpenAPI JSON | http://127.0.0.1:8000/openapi.json |

## Configuration

The frontend reads the API address from its **server process environment**, in this order:

| Variable | Behavior |
| --- | --- |
| `API_BASE_URL` | Preferred API base URL, including `/api/v1`. |
| `NASA_API_URL` | Compatibility fallback when `API_BASE_URL` is unset or empty. |
| Neither set | Uses `http://127.0.0.1:8000/api/v1`. |

For example, to use an API on port 9000:

```bash
# Linux / macOS — set before starting Streamlit
export API_BASE_URL=http://127.0.0.1:9000/api/v1
python -m streamlit run src/frontend/app.py
```

```powershell
# Windows PowerShell
$env:API_BASE_URL = "http://127.0.0.1:9000/api/v1"
.\.venv\Scripts\python.exe -m streamlit run src/frontend/app.py
```

Start Uvicorn on that port separately with `--port 9000`. Changing the frontend variable does not change the backend listener. Requests have a 15-second timeout.

The application does **not** automatically load a root `.env` file. Keep local environment files out of Git and keep passwords and access tokens out of logs and documentation.

API calls run in the Streamlit server through Python Requests, so the current frontend does not require browser CORS access. The backend does not configure CORS middleware. A future browser-side client on another origin will need appropriate CORS support or a same-origin proxy.

## Using the application

After login, open the navigation menu to access:

| View | What it shows or does |
| --- | --- |
| My Profile | Current account information from `/auth/me`. |
| Record a Measurement | One body region, a timezone-aware timestamp, `temperatura`, `caudal`, and movement flag. |
| Measurement History | Newest-first history, body-region and UTC-day filters, pagination. |
| Daily Summaries | Per-region daily sample counts, means, and movement-marked sample counts. |
| Period Analytics | Per-region means, extrema, movement fraction, and day coverage. |
| Temperature / Microcirculation | Latest readings per region on a selected UTC date, shown with body maps and individual values. |
| Measurement Reliability | Counts of samples marked as moving, grouped hourly or daily. |
| Statistical Analysis | Temperature or flow means, sample standard deviations, and reference lines by region. |

Body maps initially select the latest recorded day. A complete map requires readings for all five expected regions: neck, both arms, and both legs. Arms and legs use the more severe color of the pair. Missing regions remain visibly missing.

Sensor units are **not defined by the API**. The frontend's color thresholds and chart reference lines are presentation rules in the source; they are not validation limits enforced by the backend. Movement counts represent sensor samples with `movimiento = 1`, not independent movement events or a calibrated reliability score.

All aggregation dates use **UTC**. A seven-day window includes today so far and the previous six UTC dates. Missing samples are not zero measurements. Means use actual samples, and period means are weighted by sample count.

Sessions last one hour. An expired or revoked session returns the user to login. Logging out revokes the current token; the frontend clears its local session state.

## Project structure

```text
.
├── pyproject.toml                 # Package, optional dependencies, pytest settings
├── start_api.sh / .ps1 / .cmd    # Local API launchers
├── data/astronautas.db           # Supplied SQLite sample database
├── src/
│   ├── backend/
│   │   ├── main.py              # Application factory and startup
│   │   ├── api/                 # Health, authentication, measurement routes
│   │   ├── auth/                # Request schemas and password/token hashing
│   │   ├── measurements/        # Measurement validation
│   │   └── storage/             # SQLite persistence and aggregation
│   ├── frontend/
│   │   ├── app.py              # Streamlit entry point
│   │   ├── api.py              # Shared HTTP client and API error handling
│   │   ├── views/              # Authentication, measurements, dashboard pages
│   │   ├── components/         # Session handling, maps, charts, layout
│   │   └── assets/             # Styles and fonts
│   └── resources/              # Body-map PNG variants
├── tests/
│   ├── fixtures/astronautas.sql # Isolated test schema, not production bootstrap
│   └── test_*.py               # Backend, frontend, chart, integration tests
├── README.md
└── API.md
```

## Database behavior

The default backend resolves `data/astronautas.db` relative to its source location. There is no database-path environment variable. Tests and Python callers can provide another path through `backend.main.create_app(database_path=Path(...))`.

The database must already exist with the expected schema, including `usuarios`, `vista_usuarios`, `partes_corporales`, and `registros`. Startup opens it in read/write mode and fails rather than creating an empty replacement. Restore the supplied database if it is missing; the application does not provide a general database bootstrap or migration command.

At startup the backend creates or checks `auth_sessions`, creates `resumenes_diarios` if needed, and **rebuilds all daily summaries** from raw measurements. Collection updates affected daily summaries in the same transaction as the inserted batch. Backdated readings are supported. Duplicate submissions create additional readings; collection has no deduplication key.

The supplied database contains sample data and may be tracked in Git. Running the application changes it. Preserve a copy before experiments if you need the original sample state, and review `git status` before committing. Tests use temporary databases created from the SQL fixture and do not modify the supplied database.

Passwords use salted Argon2 hashing. Session tokens are opaque values whose SHA-256 hashes are stored in SQLite; valid sessions survive restarts until expiration or revocation. User identity for measurements always comes from authentication.

## Development and tests

Install both extras to exercise the complete frontend and backend suite:

```bash
python -m pip install -e '.[frontend,dev]'
python -m pytest -q
```

For focused backend checks:

```bash
python -m pytest tests/test_api.py tests/test_auth.py -q
```

Tests cover authentication and isolation, batch validation and atomicity, UTC windows, pagination, daily and period aggregates, latest readings, movement counts, sample statistics, API error handling, Streamlit interactions, and body-map assets. Frontend-dependent tests can be skipped when optional dependencies are absent; install the frontend extra for full coverage.

Use backend routes, schemas, storage code, and tests as the implementation authority when changing the API. Preserve Spanish JSON field names and add matching validation/error handling in the frontend. See [API.md](API.md) for the complete contract and examples.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| `No module named backend` | Install the project with the same interpreter used to start Uvicorn, or use a supplied launcher with `--app-dir src`. |
| `Cannot reach the API` | Start FastAPI, check `/api/v1/health`, and verify the frontend server's configured API URL. |
| `unable to open database file` | Restore `data/astronautas.db` and ensure the API process can write to its directory. |
| Schema or session compatibility error | Use the expected supplied schema or explicitly migrate the incompatible database; startup does not silently replace it. |
| HTTP 401 | Log in again. Tokens expire after 3,600 seconds and logout revokes the current token. |
| HTTP 409 on registration | Choose a different username/email or log in; duplicate checks are case-insensitive. |
| HTTP 422 on collection | Check the body-region ID, required fields, finite sensor values, movement flag, and timezone-aware, nonfuture timestamp. |
| Empty history or map | Confirm the authenticated user, selected UTC dates, and body-region filter. New accounts do not inherit other users' samples. |
| Missing images/fonts after installation | Run from an editable source checkout; current package-data settings do not bundle every frontend asset. |
