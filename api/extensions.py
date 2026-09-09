"""Сервисы и per-request хранилище для HTTP-слоя."""

from __future__ import annotations

import sqlite3
from typing import Optional

import flask

from db_manager import ActiveUsers, Database, PasswordService

from .config import APIConfig

# Синглтоны сервисов — потокобезопасны по своей реализации.
_passwords: Optional[PasswordService] = None
_active_users: Optional[ActiveUsers] = None


def init_extensions(app: flask.Flask, cfg: APIConfig) -> None:
    """Инициализирует сервисы и кладёт конфиг в ``app.config``."""
    global _passwords, _active_users
    _passwords = PasswordService(
        storage_path=cfg.passwords_file,
        rounds=cfg.bcrypt_rounds,
    )
    _active_users = ActiveUsers(maxlen=cfg.active_users_maxlen)
    app.config["DB_PATH"] = cfg.db_path
    app.config["_PWD_SVC"] = _passwords
    app.config["_ACTIVE_SVC"] = _active_users


def get_passwords() -> PasswordService:
    if _passwords is None:
        raise RuntimeError("PasswordService not initialized")
    return _passwords


def get_active_users() -> ActiveUsers:
    if _active_users is None:
        raise RuntimeError("ActiveUsers not initialized")
    return _active_users


def get_db_path() -> str:
    return flask.current_app.config["DB_PATH"]


def get_repository() -> "flask.g.RepositoryProxy":  # type: ignore[name-defined]
    """Возвращает репозиторий, привязанный к текущему запросу."""
    if "repo" not in flask.g:
        db_path = get_db_path()
        db = Database(db_path)
        conn = db.__enter__()
        flask.g._db = db
        flask.g._conn = conn
        from db_manager import UserRepository

        flask.g.repo = UserRepository(conn)
    return flask.g.repo


def close_db(_exc: Optional[BaseException] = None) -> None:
    """Закрывает соединение с БД по окончании запроса."""
    db = flask.g.pop("_db", None)
    flask.g.pop("_conn", None)
    flask.g.pop("repo", None)
    if db is not None:
        db.__exit__(None, None, None)