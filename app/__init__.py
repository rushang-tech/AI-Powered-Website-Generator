from __future__ import annotations

import logging
from uuid import uuid4

from flask import Flask, g, request


def create_app():
    app = Flask(__name__)

    app.config.setdefault("JSON_SORT_KEYS", False)
    app.config.setdefault("MAX_CONTENT_LENGTH", 12 * 1024 * 1024)
    app.logger.setLevel(logging.INFO)

    from app.services.ai_provider import configured_api_key_count, configured_api_key_sources

    configured_keys = configured_api_key_count()
    configured_sources = ", ".join(configured_api_key_sources()) or "none"
    log_message = "ai.provider.startup configured_gemini_keys=%s sources=%s"
    if configured_keys <= 1:
        app.logger.warning(log_message, configured_keys, configured_sources)
    else:
        app.logger.info(log_message, configured_keys, configured_sources)

    @app.before_request
    def attach_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        app.logger.info("request.start id=%s method=%s path=%s", g.request_id, request.method, request.path)

    @app.after_request
    def add_request_id(response):
        request_id = getattr(g, "request_id", "")
        if request_id:
            response.headers["X-Request-ID"] = request_id
            app.logger.info("request.end id=%s status=%s", request_id, response.status_code)
        return response

    from app.routes import main
    app.register_blueprint(main)

    return app
