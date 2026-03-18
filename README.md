# AI-Powered Website Generator

## Quickstart

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the app

```bash
python run.py
```

The app starts on `http://localhost:5001` by default.

### 4) Run tests

```bash
PYTHONPATH=. pytest
```

`pytest.ini` is included so tests can import `app` during collection.

## Preview Storage

- Default (local dev): in-memory preview store.
- Production-ready: set `REDIS_URL` to enable Redis-backed preview storage with TTL and shared state across instances.

Optional env vars:

- `PREVIEW_TTL_SECONDS` (default: `3600`)
- `PREVIEW_MAX_ITEMS` (default: `200`)
- `PREVIEW_KEY_PREFIX` (default: `velosite:preview`)

## Existing Project Documentation

- **[View WBS (Diagram)](https://github.com/rushang-tech/AI-Powered-Website-Generator/blob/1f14ff6ce91a7f99ff8a6821001643b1c92c0b1d/assets/AI-Power-Website_generator-WBS.png)**
- **[View Gantt Chart (Timeline)](https://github.com/rushang-tech/AI-Powered-Website-Generator/blob/1f14ff6ce91a7f99ff8a6821001643b1c92c0b1d/assets/AI-Power-Website_generator-Gantt-Chart.jpg)**
