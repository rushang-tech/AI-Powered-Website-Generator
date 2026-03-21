from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 1)


def gunicorn_worker_count(default_workers: int = 2) -> int:
    configured = _int_env("WEB_CONCURRENCY", default_workers)
    redis_url = os.environ.get("REDIS_URL", "").strip()
    return configured if redis_url else 1
