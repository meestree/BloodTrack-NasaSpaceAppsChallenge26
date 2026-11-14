# Project context

Do not automatically read the root `.env`, files in `docs/`, or other project
reference documents. Read them only when the user explicitly invokes the
`Read docs` task, for example by saying `Run Read docs`. The task definition is
in `tasks/read-docs.md`; read and execute it when invoked. Merely starting a
session or receiving a development request does not invoke this task.

This restriction does not prevent reading source code, tests, configuration
needed for an implementation, or applicable AGENTS.md instructions. If a task
needs reference documentation that has not been authorized, ask the user to
invoke `Read docs` rather than opening the documents automatically.

Treat environment variable values as potentially sensitive. Do not reproduce
them in replies, logs, commits, or documentation. The `.env` file is local and
must remain excluded from Git.

## Frontend development focus

The current development focus is building the frontend for the existing backend.
The backend has been merged into `main`, and the previous local `frontend`
branch has been deleted. Work on the current branch unless the user requests a
branch change; do not assume that a `frontend` branch exists.

Build the interface around registration, login, the current user's profile,
body-part selection, measurement collection, history, daily summaries, and
period analytics. Match the backend's request and response field names, including
the Spanish names. Provide loading, empty, success, validation, and error states.
Do not invent sensor units or interpret missing samples as zero measurements.

Keep the API base URL configurable. Use the real API for integration and keep
any development fixtures clearly separate from live data. Never connect the
frontend directly to SQLite. Check backend configuration before relying on
cross-origin requests; configure a development proxy or appropriate backend CORS
support if the frontend and API run on different origins.

## Backend overview for frontend integration

- The backend is a Python 3.11+ FastAPI application in `src/backend/`.
  The entry point is `backend.main:app`; run it with
  `uvicorn backend.main:app --reload` after installing the project dependencies.
- The default local API base URL is `http://127.0.0.1:8000/api/v1`.
  Runtime API documentation is available at `/docs`, `/redoc`, and
  `/openapi.json`. Reading project reference files still requires the
  `Read docs` task described above.
- Public endpoints: `GET /health`, `POST /auth/register`, and
  `POST /auth/login` (all relative to `/api/v1`). Registration accepts
  `nombre_usuario`, `password`, `email`, and `fecha_nacimiento` (`YYYY-MM-DD`);
  login accepts `nombre_usuario` and `password`.
- Login returns `access_token`, `token_type`, and `expires_in` (3,600 seconds).
  Protected requests require `Authorization: Bearer <access_token>`.
  `GET /auth/me` returns the current user; `POST /auth/logout` revokes the
  current token and returns an empty HTTP 204 response. Handle expired or
  revoked sessions (HTTP 401) by returning the user to login.
- `GET /body-parts` returns the valid `id_parte` and `nombre` values.
  `POST /measurements` accepts a `measurements` array of 1–1,000 items, each
  containing `id_parte`, `timestamp`, `temperatura`, `caudal`, and `movimiento`
  (0 or 1). Timestamps must include a timezone and cannot be in the future.
  Extra payload fields are rejected; do not submit an `id_usuario`.
- `GET /measurements`, `GET /measurements/daily`, and
  `GET /measurements/analytics` accept `days` (default 7, range 1–3,650) and
  optional `id_parte`. Raw history also accepts `limit` (default 100, maximum
  1,000) and `offset` (default 0). History returns `total`, `limit`, `offset`,
  and `items`; daily summaries and analytics return `items`. All three return
  `from` and `to`; analytics also returns `days`.
- Time windows and daily grouping use UTC calendar dates. `days=1` means today
  so far. History is newest first. All measurement access is scoped to the
  authenticated user. Parts or dates with no samples are omitted from summaries.
- Errors use a JSON `detail` field: a string for authentication, duplicate
  accounts (HTTP 409), or unknown body parts (HTTP 422); an array with `type`,
  `loc`, and `msg` for request validation errors (HTTP 422). Map field errors
  to the relevant form inputs without logging passwords or tokens.
- The database is `data/astronautas.db`; it must already contain the expected
  schema. It contains sample data, not real user information, and may be tracked
  in Git. Backend source, schemas, and tests are the implementation authority
  when checking integration behavior.
