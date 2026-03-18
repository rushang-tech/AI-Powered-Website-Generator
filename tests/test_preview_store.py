import unittest

from app.services.preview_store import InMemoryPreviewStore


class PreviewStoreTests(unittest.TestCase):
    def test_get_refreshes_item_and_cleanup_removes_expired(self):
        store = InMemoryPreviewStore(ttl_seconds=0, max_items=2)
        store.set(preview_id="one", prompt="Prompt", payload={"preview_id": "one"})
        self.assertIsNone(store.get("one"))

    def test_store_evicts_oldest_item_when_max_items_exceeded(self):
        store = InMemoryPreviewStore(ttl_seconds=60, max_items=2)
        store.set(preview_id="one", prompt="Prompt", payload={"preview_id": "one"})
        store.set(preview_id="two", prompt="Prompt", payload={"preview_id": "two"})
        store.set(preview_id="three", prompt="Prompt", payload={"preview_id": "three"})
        self.assertIsNone(store.get("one"))
        self.assertIsNotNone(store.get("two"))
        self.assertIsNotNone(store.get("three"))


if __name__ == "__main__":
    unittest.main()
