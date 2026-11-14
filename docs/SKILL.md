---
name: docs
description: Requirements of the project
---

# AGENTS.md — NASA Space Apps

## Project context
Python application to monitor physiological indicators related to fluid redistribution in microgravity.

The system collects measurements from 5 body regions:
- `left_arm`
- `right_arm`
- `left_leg`
- `right_leg`
- `neck_lateral`

No chest sensors.

## Tech stack
- Python 3
- Streamlit (frontend)
- Plotly (interactive charts)
- Pandas / NumPy (data processing)
- JSON (sensor communication)
- GitHub (collaboration)

## Sensor data
All 5 regions are transmitted together in one JSON payload with a shared timestamp.

Measurements:
- **Temperature:** `celsius degree` (C), all 5 regions.
- **Skin temperature:** `skin_temperature_c` (°C), 4 extremities.
- **Movement:** `boolean` checks if the astronaut is moving during the data recopilation

Use `null` for missing optional measurements.

## Scientific constraints
- Bioimpedance does NOT directly measure blood volume.
- Impedance changes may indicate relative changes in tissue fluid content.
- Compare each region against its own baseline.
- Never interpret impedance changes as exact blood accumulation.
- Do not invent physiological formulas or sensor measurements.
- Clearly distinguish simulated data from real measurements.

## Architecture
Separate responsibilities into:
- `ingestion/`: receive and validate JSON.
- `processing/`: baselines, calculations and trends.
- `simulation/`: synthetic sensor data.
- `dashboard/`: Streamlit UI and Plotly charts.
- `storage/`: measurement history.

## Development rules
- Write clean, modular Python with type hints.
- Use English for code identifiers.
- Keep processing logic separate from UI.
- Preserve JSON field names and measurement units.
- Avoid unnecessary dependencies and abstractions.
- Do not modify unrelated files.
- Add tests for data validation and processing.
- Prefer small, focused changes.
- Review existing code before implementing new functionality.

## Main goal
Build an interactive Streamlit dashboard displaying current measurements, baseline-relative variations, body-region comparisons and historical trends.

Prioritize scientific accuracy, simplicity and a functional prototype.

