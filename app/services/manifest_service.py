from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

from app.services.contracts import ProjectManifest
from app.services.preview_store import PREVIEW_STORE


class ManifestStore(Protocol):
    def set(self, *, preview_id: str, prompt: str, payload: dict[str, Any]) -> None:
        ...

    def get(self, preview_id: str) -> dict[str, Any] | None:
        ...


class ManifestService:
    def __init__(self, store: ManifestStore) -> None:
        self._store = store

    def save(self, manifest: ProjectManifest) -> ProjectManifest:
        self._store.set(
            preview_id=manifest.preview_id,
            prompt=manifest.prompt,
            payload=manifest.to_dict(),
        )
        return manifest

    def get(self, preview_id: str) -> ProjectManifest | None:
        item = self._store.get(preview_id)
        if not item:
            return None
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if not payload:
            return None
        return ProjectManifest.from_dict(deepcopy(payload))

    def update(self, manifest: ProjectManifest) -> ProjectManifest:
        return self.save(manifest)


MANIFEST_SERVICE = ManifestService(PREVIEW_STORE)
