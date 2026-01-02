from __future__ import annotations

import logging
import os
from uuid import uuid4

from flask import Flask, g, request

from app.extensions import db, login_manager


def create_app(test_config: dict[str, object] | None = None):
    app = Flask(__name__, instance_relative_config=True)

    default_database_path = os.path.join(app.instance_path, "velosite.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "velosite-local-dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{default_database_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    app.config.setdefault("JSON_SORT_KEYS", False)
    app.config.setdefault("MAX_CONTENT_LENGTH", 12 * 1024 * 1024)
    app.logger.setLevel(logging.INFO)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

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

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if not user_id.isdigit():
            return None
        return db.session.get(User, int(user_id))

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app
