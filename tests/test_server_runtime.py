import os
import unittest
from unittest.mock import patch

from app.server_runtime import gunicorn_worker_count


class GunicornWorkerCountTests(unittest.TestCase):
    def test_defaults_to_single_worker_without_redis(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(gunicorn_worker_count(), 1)

    def test_uses_configured_workers_when_redis_is_available(self):
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0", "WEB_CONCURRENCY": "3"}, clear=True):
            self.assertEqual(gunicorn_worker_count(), 3)

    def test_uses_default_worker_count_when_redis_is_available_and_concurrency_missing(self):
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0"}, clear=True):
            self.assertEqual(gunicorn_worker_count(), 2)
