import os
import unittest
from unittest.mock import patch

from app.server_runtime import gunicorn_worker_count, resolve_bind_port


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


class PortResolutionTests(unittest.TestCase):
    def test_uses_default_port_when_available(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.server_runtime._can_bind", return_value=True):
                selection = resolve_bind_port()

        self.assertEqual(selection.port, 5001)
        self.assertEqual(selection.requested_port, 5001)
        self.assertFalse(selection.from_env)
        self.assertFalse(selection.auto_selected)

    def test_moves_to_next_available_port_when_default_is_busy(self):
        def can_bind(_host: str, port: int) -> bool:
            return port == 5003

        with patch.dict(os.environ, {}, clear=True):
            with patch("app.server_runtime._can_bind", side_effect=can_bind):
                selection = resolve_bind_port(search_limit=5)

        self.assertEqual(selection.port, 5003)
        self.assertEqual(selection.requested_port, 5001)
        self.assertFalse(selection.from_env)
        self.assertTrue(selection.auto_selected)

    def test_uses_explicit_port_without_auto_selecting(self):
        with patch.dict(os.environ, {"PORT": "6100"}, clear=True):
            with patch("app.server_runtime._can_bind") as can_bind:
                selection = resolve_bind_port()

        self.assertEqual(selection.port, 6100)
        self.assertEqual(selection.requested_port, 6100)
        self.assertTrue(selection.from_env)
        self.assertFalse(selection.auto_selected)
        can_bind.assert_not_called()

    def test_rejects_invalid_explicit_port(self):
        with patch.dict(os.environ, {"PORT": "not-a-number"}, clear=True):
            with self.assertRaisesRegex(ValueError, "PORT must be an integer."):
                resolve_bind_port()
