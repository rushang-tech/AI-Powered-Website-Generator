from __future__ import annotations

import json
import os
import time
from collections import OrderedDict
from typing import Any

try:
    from redis import Redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - redis is optional for local dev
    Redis = None  # type: ignore[assignment]

    class RedisError(Exception):
        pass


class InMemoryPreviewStore:
    def __init__(self, *, ttl_seconds: int = 3600, max_items: int = 200) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self._items: "OrderedDict[str, dict[str, Any]]" = OrderedDict()

    def _cleanup(self) -> None:
        now = time.time()
        expired_ids = []
        for preview_id, item in self._items.items():
            if now - item["updated_at"] > self.ttl_seconds:
                expired_ids.append(preview_id)
        for preview_id in expired_ids:
            self._items.pop(preview_id, None)

        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def set(self, *, preview_id: str, prompt: str, payload: dict[str, Any]) -> None:
        self._cleanup()
        self._items.pop(preview_id, None)
        self._items[preview_id] = {
            "preview_id": preview_id,
            "prompt": prompt,
            "payload": payload,
            "updated_at": time.time(),
        }

    def get(self, preview_id: str) -> dict[str, Any] | None:
        self._cleanup()
        item = self._items.get(preview_id)
        if not item:
            return None
        item["updated_at"] = time.time()
        self._items.move_to_end(preview_id)
        return item

    def clear(self) -> None:
        self._items.clear()


class RedisPreviewStore:
    def __init__(
        self,
        *,
        redis_url: str,
        ttl_seconds: int = 3600,
        max_items: int = 200,
        key_prefix: str = "velosite:preview",
    ) -> None:
        if Redis is None:
            raise RuntimeError("redis package is not installed")
        self.ttl_seconds = ttl_seconds
        self.max_items = max_items
        self.key_prefix = key_prefix
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._index_key = f"{key_prefix}:index"

    def _item_key(self, preview_id: str) -> str:
        return f"{self.key_prefix}:item:{preview_id}"

    def _evict_if_needed(self) -> None:
        total = int(self._redis.zcard(self._index_key) or 0)
        if total <= self.max_items:
            return

        evict_count = total - self.max_items
        stale_ids = self._redis.zrange(self._index_key, 0, evict_count - 1)
        if not stale_ids:
            return

        pipe = self._redis.pipeline()
        pipe.zrem(self._index_key, *stale_ids)
        pipe.delete(*[self._item_key(item_id) for item_id in stale_ids])
        pipe.execute()

    def set(self, *, preview_id: str, prompt: str, payload: dict[str, Any]) -> None:
        now = time.time()
        item = {
            "preview_id": preview_id,
            "prompt": prompt,
            "payload": payload,
            "updated_at": now,
        }
        encoded = json.dumps(item)

        pipe = self._redis.pipeline()
        pipe.set(self._item_key(preview_id), encoded, ex=self.ttl_seconds)
        pipe.zadd(self._index_key, {preview_id: now})
        pipe.execute()

        self._evict_if_needed()

    def get(self, preview_id: str) -> dict[str, Any] | None:
        key = self._item_key(preview_id)
        raw = self._redis.get(key)
        if raw is None:
            self._redis.zrem(self._index_key, preview_id)
            return None

        parsed = json.loads(raw)
        now = time.time()
        parsed["updated_at"] = now

        pipe = self._redis.pipeline()
        pipe.set(key, json.dumps(parsed), ex=self.ttl_seconds)
        pipe.zadd(self._index_key, {preview_id: now})
        pipe.execute()

        return parsed if isinstance(parsed, dict) else None

    def clear(self) -> None:
        ids = self._redis.zrange(self._index_key, 0, -1)
        pipe = self._redis.pipeline()
        if ids:
            pipe.delete(*[self._item_key(item_id) for item_id in ids])
        pipe.delete(self._index_key)
        pipe.execute()


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, 1)


def create_preview_store() -> InMemoryPreviewStore | RedisPreviewStore:
    ttl_seconds = _int_env("PREVIEW_TTL_SECONDS", 3600)
    max_items = _int_env("PREVIEW_MAX_ITEMS", 200)
    redis_url = os.environ.get("REDIS_URL", "").strip()
    key_prefix = os.environ.get("PREVIEW_KEY_PREFIX", "velosite:preview").strip() or "velosite:preview"

    if redis_url and Redis is not None:
        try:
            store = RedisPreviewStore(
                redis_url=redis_url,
                ttl_seconds=ttl_seconds,
                max_items=max_items,
                key_prefix=key_prefix,
            )
            store._redis.ping()
            return store
        except (RedisError, RuntimeError):
            pass

    return InMemoryPreviewStore(ttl_seconds=ttl_seconds, max_items=max_items)


PREVIEW_STORE = create_preview_store()
