from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any


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


PREVIEW_STORE = InMemoryPreviewStore()
