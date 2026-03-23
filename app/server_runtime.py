from __future__ import annotations

from dataclasses import dataclass
import os
import socket


DEFAULT_LOCAL_PORT = 5001
LOCAL_PORT_SEARCH_LIMIT = 25


@dataclass(frozen=True)
class PortSelection:
    port: int
    requested_port: int | None
    from_env: bool
    auto_selected: bool


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


def _parse_port(raw: str, env_name: str = "PORT") -> int:
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer.") from exc
    if not 0 <= port <= 65535:
        raise ValueError(f"{env_name} must be between 0 and 65535.")
    return port


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def resolve_bind_port(
    default_port: int = DEFAULT_LOCAL_PORT,
    search_limit: int = LOCAL_PORT_SEARCH_LIMIT,
    host: str = "0.0.0.0",
) -> PortSelection:
    configured_port = os.environ.get("PORT", "").strip()
    if configured_port:
        port = _parse_port(configured_port)
        return PortSelection(port=port, requested_port=port, from_env=True, auto_selected=False)

    for candidate in range(default_port, default_port + search_limit + 1):
        if _can_bind(host, candidate):
            return PortSelection(
                port=candidate,
                requested_port=default_port,
                from_env=False,
                auto_selected=candidate != default_port,
            )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        port = int(sock.getsockname()[1])

    return PortSelection(port=port, requested_port=default_port, from_env=False, auto_selected=True)
