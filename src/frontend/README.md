# Streamlit frontend

From the repository root, install the frontend extra into your Python environment:

```sh
python -m pip install -e '.[frontend]'
python -m streamlit run src/frontend/app.py
```

Run from the repository root so Streamlit loads `.streamlit/config.toml`.

```text
src/frontend/
├── app.py                  # Entry point and page registration
├── assets/styles.css       # Responsive page and component styles
├── components/
│   ├── body_map.py          # Reserved body map area
│   ├── layout.py            # App shell and navigation
│   └── legend.py            # Accessible temperature color legend
├── figma/                  # Reserved for design files from the other branch
└── views/temperature.py    # Temperature page composition
```

Register future views with `st.Page` in `app.py` and add their links in the
shared sidebar. Keep shared presentation elements in `components` and static
files in `assets`; the Figma directory is reserved for design source files.

The temperature map signs in through the API and loads the latest measurement
per body part on the latest recorded UTC date. The date input selects another
UTC day. Each pair of limbs takes its most severe temperature color; individual
readings and their timestamps are shown below. Missing measurements never become
green or zero; incomplete dates display the available readings without a map.

Set `API_BASE_URL` to override `http://127.0.0.1:8000/api/v1`. Requests run on the
Streamlit server, so the browser does not make cross-origin requests to FastAPI.
No frontend component opens SQLite. Run the backend separately:

```sh
python -m uvicorn backend.main:app --reload
```

`GET /measurements/latest` is authenticated and defaults to the latest recorded
UTC date for the current user. Pass `date=YYYY-MM-DD` for a specific day. It
returns `date` and `items`, with the latest measurement per part (timestamp ties
use the highest record ID). No records returns an empty `items` array.

Images remain in `src/resources/H{color}_A{color}_L{color}.png`. The map uses
35.5–37°C as green, below 34.5 or above 39 as red, and the remaining values as
yellow (including the gap from 38.9 through 39). These are the supplied app
thresholds. Tokens stay in individual Streamlit session state; expired or
revoked tokens return the map to its sign-in form.

The **Microcirculation** sidebar page shares the authenticated map and date
controls, using `caudal` instead of `temperatura`. For the neck, values below
300 or above 950 are red, 300–699 and 850–950 are yellow, and the interval
between is green. For limbs, below 300 or above 20000 is red, 750–1000 inclusive is green,
and all other values are yellow, including values strictly between 1000 and 1500. Each pair displays
its more severe side. These are the project reference ranges supplied for
this visualization.

**Measurement reliability** uses `GET /measurements/movement` with inclusive
`start_date` and `end_date` query parameters (UTC, up to 3650 days, no future
dates). One date groups by hour; multiple dates group by day. The authenticated
endpoint optionally accepts `id_parte`. Each returned item contains `periodo`,
`muestras` (total samples), and `movimiento_unos` (samples marked as moving).
The page counts samples across all body parts, not unique physical movement
events or movement intensity. Missing sampling periods remain gaps in the
chart. A recorded period with no movement flags has an actual zero count.

The **Statistical Analysis** buttons now open temperature or microcirculation
charts on the same page. One selected day uses hourly bins; a date range uses
daily bins. Separate neck, arms, and legs charts keep both limb sides distinct.
Lines show per-bin sample means, bands show ±1 sample standard deviation
(`n - 1` denominator), and dashed green lines show supplied normal references.
A single sample has no defined sample standard deviation. Missing bins have no
mean or band and remain gaps. Charts do not combine limb measurements into an
artificial aggregate. The statistics table includes counts, means, sample SDs,
minimums, and maximums in the selected metric's units.

`GET /measurements/statistics?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&metric=temperatura`
is authenticated and user-scoped. Use `metric=caudal` for microcirculation;
responses include `from`, `to`, `metric`, `granularity`, and `items` with
`id_parte`, `nombre`, `periodo`, `muestras`, `media`, `desviacion_estandar`,
`minimo`, and `maximo`. Date constraints match the reliability endpoint.
