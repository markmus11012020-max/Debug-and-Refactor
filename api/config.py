"""Конфигурация HTTP API."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class APIConfig:
    """Неизменяемая конфигурация Flask-приложения."""

    db_path: str = "users.db"
    passwords_file: str = "passwords.txt"
    bcrypt_rounds: int = 12
    active_users_maxlen: int = 5
    host: str = "127.0.0.1"
    port: int = 5000
    debug: bool = False

    @classmethod
    def from_env(cls) -> "APIConfig":
        return cls(
            db_path=os.environ.get("DB_PATH", "users.db"),
            passwords_file=os.environ.get("PASSWORDS_FILE", "passwords.txt"),
            bcrypt_rounds=_get_int("BCRYPT_ROUNDS", 12),
            active_users_maxlen=_get_int("ACTIVE_USERS_MAXLEN", 5),
            host=os.environ.get("API_HOST", "127.0.0.1"),
            port=_get_int("API_PORT", 5000),
            debug=_get_bool("API_DEBUG", False),
        )