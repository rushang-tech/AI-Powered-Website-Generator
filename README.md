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

### 3) Add your Gemini API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then set at least one key:

```bash
GEMINI_API_KEY=your_key_here
```

If you want robust rotation across a pool of Gemini keys, use either:

```bash
GEMINI_API_KEYS=key1,key2,key3
```

or numbered entries:

```bash
GEMINI_API_KEY_1=key1
GEMINI_API_KEY_2=key2
GEMINI_API_KEY_3=key3
```

Optional:

- `GEMINI_API_KEYS` as a comma-separated list to rotate through multiple keys (`key1,key2,key3`)
- `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, ... as numbered key entries (alternative rotation format)
- `GEMINI_MODEL` to override the default model (`gemini-2.5-flash-lite`)
- `GEMINI_FALLBACK_MODELS` as a comma-separated list of backup Gemini models
- `GEMINI_ROTATION_RETRY_ROUNDS` to control extra retry passes across keys for transient 429/5xx failures
- `GEMINI_ROTATION_RETRY_BACKOFF_SECONDS` to control backoff between retry rounds

The app also accepts `GOOGLE_API_KEY`, `GOOGLE_API_KEYS`, and `GOOGLE_API_KEY_1` style aliases.
When multiple keys are configured, the app now tries fallback models on each key before rotating and can make another bounded pass for transient rate-limit/server failures.

### 4) Run the app

```bash
python run.py
```

The app starts on `http://localhost:5001` by default.

### 5) Run tests

```bash
PYTHONPATH=. pytest
```

`pytest.ini` is included so tests can import `app` during collection.

## Production Deployment (Render)

This repo is now configured for Render with a production server (`gunicorn`) and a health endpoint (`/healthz`).

### 1) Push this repo to GitHub

Render will pull and auto-deploy from your connected GitHub repository.

### 2) Create a new Web Service from this repo

Render uses `render.yaml` automatically:

- Build command: `pip install -r requirements.txt`
- Start command: `python start_gunicorn.py`
- Health check path: `/healthz`

### 3) Set required environment variables in Render

- `GEMINI_API_KEY` (required for AI generation if you are not using multi-key rotation vars)
- `GEMINI_API_KEYS` (optional, comma-separated key rotation list)
- `GEMINI_API_KEY_1` / `GEMINI_API_KEY_2` / ... (optional, numbered key rotation entries)
- `GEMINI_MODEL` (optional, defaults to `gemini-2.5-flash-lite`)
- `GEMINI_FALLBACK_MODELS` (optional, comma-separated backup models to try before switching keys)
- `GEMINI_ROTATION_RETRY_ROUNDS` (optional, defaults to `2`)
- `GEMINI_ROTATION_RETRY_BACKOFF_SECONDS` (optional, defaults to `0.35`)
- `REDIS_URL` (recommended if you want more than one web worker)

Optional:

- `PREVIEW_TTL_SECONDS` (default `3600`)
- `PREVIEW_MAX_ITEMS` (default `200`)
- `PREVIEW_KEY_PREFIX` (default `velosite:preview`)

### 4) Add Redis (recommended)

Create a managed Redis instance and copy its connection string into `REDIS_URL`.
Without Redis, preview and published-site data use in-memory storage. `start_gunicorn.py` automatically falls back to a single worker in that case so Studio buttons like regenerate, publish, and export keep reading the same in-memory state.

### 5) Verify after deploy

Run these checks against your Render URL:

```bash
curl https://<your-service>.onrender.com/healthz
curl -X POST https://<your-service>.onrender.com/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A SaaS landing page for an AI analytics product"}'
```

### 6) Publish generated websites to a live link

In Studio, click **Publish Link**.
This creates a share URL like:

`https://<your-service>.onrender.com/published/<publish_id>`

API equivalent:

```bash
curl -X POST https://<your-service>.onrender.com/preview/<preview_id>/publish \
  -H "Content-Type: application/json" \
  -d '{"variant_id":"variant-1"}'
```

Optional publish env vars:

- `PUBLISHED_TTL_SECONDS` (default `2592000`, 30 days)
- `PUBLISHED_MAX_ITEMS` (default `500`)
- `PUBLISHED_KEY_PREFIX` (default `velosite:published`)
- `PUBLISHED_REDIS_URL` (falls back to `REDIS_URL` if unset)

## Preview Storage

- Default (local dev): in-memory preview store.
- Safe production fallback: one Gunicorn worker when `REDIS_URL` is unset.
- Production-ready: set `REDIS_URL` to enable Redis-backed preview storage with TTL and shared state across workers.

Optional env vars:

- `PREVIEW_TTL_SECONDS` (default: `3600`)
- `PREVIEW_MAX_ITEMS` (default: `200`)
- `PREVIEW_KEY_PREFIX` (default: `velosite:preview`)

## Existing Project Documentation

- **[View WBS (Diagram)](https://github.com/rushang-tech/AI-Powered-Website-Generator/blob/1f14ff6ce91a7f99ff8a6821001643b1c92c0b1d/assets/AI-Power-Website_generator-WBS.png)**
- **[View Gantt Chart (Timeline)](https://github.com/rushang-tech/AI-Powered-Website-Generator/blob/1f14ff6ce91a7f99ff8a6821001643b1c92c0b1d/assets/AI-Power-Website_generator-Gantt-Chart.jpg)**
