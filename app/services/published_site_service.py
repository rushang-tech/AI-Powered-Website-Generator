from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Protocol

from app.services.preview_store import InMemoryPreviewStore, Redis, RedisError, RedisPreviewStore


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 1)


class PublishedStore(Protocol):
    def set(self, *, preview_id: str, prompt: str, payload: dict[str, Any]) -> None:
        ...

    def get(self, preview_id: str) -> dict[str, Any] | None:
        ...

    def clear(self) -> None:
        ...


class PublishedSiteService:
    def __init__(self, store: PublishedStore, *, ttl_seconds: int) -> None:
        self._store = store
        self.ttl_seconds = ttl_seconds

    def save(self, publish_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = dict(payload)
        record.setdefault("publish_id", publish_id)
        record.setdefault("published_at", datetime.now(UTC).isoformat())
        self._store.set(
            preview_id=publish_id,
            prompt=str(record.get("page_title", "")),
            payload=record,
        )
        return record

    def get(self, publish_id: str) -> dict[str, Any] | None:
        item = self._store.get(publish_id)
        if not item:
            return None
        payload = item.get("payload")
        return payload if isinstance(payload, dict) else None

    def clear(self) -> None:
        self._store.clear()


PUBLISHED_TTL_SECONDS = _int_env("PUBLISHED_TTL_SECONDS", 60 * 60 * 24 * 30)
PUBLISHED_MAX_ITEMS = _int_env("PUBLISHED_MAX_ITEMS", 500)
PUBLISHED_KEY_PREFIX = os.environ.get("PUBLISHED_KEY_PREFIX", "velosite:published").strip() or "velosite:published"
PUBLISHED_REDIS_URL = os.environ.get("PUBLISHED_REDIS_URL", "").strip() or os.environ.get("REDIS_URL", "").strip()


def create_published_site_service() -> PublishedSiteService:
    if PUBLISHED_REDIS_URL and Redis is not None:
        try:
            store = RedisPreviewStore(
                redis_url=PUBLISHED_REDIS_URL,
                ttl_seconds=PUBLISHED_TTL_SECONDS,
                max_items=PUBLISHED_MAX_ITEMS,
                key_prefix=PUBLISHED_KEY_PREFIX,
            )
            store._redis.ping()
            return PublishedSiteService(store, ttl_seconds=PUBLISHED_TTL_SECONDS)
        except (RedisError, RuntimeError):
            pass

    return PublishedSiteService(
        InMemoryPreviewStore(ttl_seconds=PUBLISHED_TTL_SECONDS, max_items=PUBLISHED_MAX_ITEMS),
        ttl_seconds=PUBLISHED_TTL_SECONDS,
    )


PUBLISHED_SITE_SERVICE = create_published_site_service()
