from __future__ import annotations

import logging
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, g, request
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, login_manager


def create_app(test_config: dict[str, object] | None = None):
    _load_environment_files()
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    default_database_path = os.path.join(app.instance_path, "velosite.db")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "velosite-local-dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{default_database_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        GOOGLE_OAUTH_CLIENT_ID=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        GOOGLE_OAUTH_CLIENT_SECRET=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        GOOGLE_OAUTH_DISCOVERY_URL=os.environ.get(
            "GOOGLE_OAUTH_DISCOVERY_URL",
            "https://accounts.google.com/.well-known/openid-configuration",
        ),
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
        _ensure_user_auth_columns()

    return app


def _load_environment_files() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    example_env_path = project_root / ".env.example"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    elif example_env_path.exists():
        load_dotenv(dotenv_path=example_env_path, override=False)


def _ensure_user_auth_columns() -> None:
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []

    if "google_sub" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)")
    if "avatar_url" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512) NOT NULL DEFAULT ''")
    if "auth_provider" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(32) NOT NULL DEFAULT 'password'")
    if "email_verified" not in columns:
        default_bool = "0" if db.engine.dialect.name == "sqlite" else "FALSE"
        statements.append(f"ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT {default_bool}")

    with db.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)"))
