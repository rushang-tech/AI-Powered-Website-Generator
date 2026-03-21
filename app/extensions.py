from __future__ import annotations

from flask import jsonify, redirect, request, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def expects_json_response() -> bool:
    path = request.path or ""
    if request.is_json:
        return True
    if request.method != "GET":
        return True
    if path.startswith("/conversations"):
        return True
    accept = request.accept_mimetypes
    return (
        accept.best == "application/json"
        and accept["application/json"] > accept["text/html"]
    )


@login_manager.unauthorized_handler
def _handle_unauthorized():
    if expects_json_response():
        return jsonify({"error": "Authentication required."}), 401
    return redirect(url_for("main.login", next=request.path))
