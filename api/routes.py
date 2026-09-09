"""HTTP-эндпоинты проекта."""

from __future__ import annotations

import flask

from .errors import NotFoundError, ValidationError
from .extensions import (
    get_active_users,
    get_passwords,
    get_repository,
)
from .schemas import validate_create_user

bp = flask.Blueprint("api", __name__)


@bp.get("/health")
def health() -> flask.Response:
    return flask.jsonify({"status": "ok"})


@bp.post("/users")
def create_user() -> tuple[flask.Response, int]:
    name, tags = validate_create_user(flask.request.get_json(silent=True))
    repo = get_repository()
    new_id = repo.add_user(name, tags)
    user = repo.get_user_by_id(new_id)
    assert user is not None  # только что вставили
    flask.current_app.logger.info("user created: id=%s name=%s", new_id, name)
    return flask.jsonify(user), 201


@bp.get("/users/<int:user_id>")
def get_user(user_id: int) -> flask.Response:
    user = get_repository().get_user_by_id(user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} not found")
    return flask.jsonify(user)


@bp.get("/users")
def list_users() -> flask.Response:
    return flask.jsonify(get_repository().list_users())


@bp.get("/active")
def active_users() -> flask.Response:
    return flask.jsonify(get_active_users().snapshot())


@bp.post("/users/<int:user_id>/password")
def set_password(user_id: int) -> tuple[flask.Response, int]:
    payload = flask.request.get_json(silent=True)
    if not isinstance(payload, dict) or "password" not in payload:
        raise ValidationError("'password' is required")
    password = payload["password"]
    if not isinstance(password, str) or not password:
        raise ValidationError("'password' must be a non-empty string")

    user = get_repository().get_user_by_id(user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} not found")

    hashed = get_passwords().store(user_id, password)
    return flask.jsonify({"id": user_id, "hashed": True, "preview": hashed[:7] + "..."}), 201