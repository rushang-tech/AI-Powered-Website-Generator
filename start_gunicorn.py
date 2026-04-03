from __future__ import annotations

import os

from app.server_runtime import gunicorn_worker_count


def main() -> None:
    port = os.environ.get("PORT", "5001").strip() or "5001"
    threads = os.environ.get("GUNICORN_THREADS", "4").strip() or "4"
    timeout = os.environ.get("GUNICORN_TIMEOUT", "120").strip() or "120"
    workers = str(gunicorn_worker_count())

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
