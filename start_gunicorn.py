from __future__ import annotations

import os

from app.server_runtime import gunicorn_worker_count, resolve_bind_port


def main() -> None:
    selection = resolve_bind_port()
    threads = os.environ.get("GUNICORN_THREADS", "4").strip() or "4"
    timeout = os.environ.get("GUNICORN_TIMEOUT", "120").strip() or "120"
    workers = str(gunicorn_worker_count())
    port = str(selection.port)

    if selection.auto_selected:
        print(
            f"Port {selection.requested_port} is already in use. "
            f"Starting Gunicorn on port {selection.port} instead.",
            flush=True,
        )
    else:
        print(f"Starting Gunicorn on port {selection.port}.", flush=True)

    args = [
        "gunicorn",
        "--bind",
        f"0.0.0.0:{port}",
        "--workers",
        workers,
        "--threads",
        threads,
        "--timeout",
        timeout,
        "run:app",
    ]
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()
