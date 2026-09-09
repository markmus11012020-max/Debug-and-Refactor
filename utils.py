"""Обратно-совместимый фасад к пакету db_manager.

Сохранён публичный API из исходного ``utils.py``, но реализация
перенесена в пакет ``db_manager`` (см. db_manager/*).

Использование:
    from utils import add_user, store_password, get_user_by_name
    uid = add_user("alice", tags=["vip"])
    store_password(uid, "s3cret!")
    user = get_user_by_name("alice")
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from db_manager import (
    ActiveUsers,
    Database,
    PasswordService,
    UserRepository,
)


# Глобальные сервисы (singleton'ы) — потокобезопасны по своей реализации.
_active = ActiveUsers(maxlen=5)
_passwords = PasswordService(storage_path="passwords.txt", rounds=12)


def add_user(
    name: str,
    tags: Optional[Iterable[str]] = None,
    *,
    db_path: str = "users.db",
) -> int:
    """Добавляет пользователя; возвращает ``int`` id.

    Оригинальный список ``tags`` не модифицируется.
    """
    tags_list = list(tags) if tags is not None else None
    with Database(db_path) as conn:
        repo = UserRepository(conn)
        return repo.add_user(name, tags_list)


def get_user_by_name(
    name: str, *, db_path: str = "users.db"
) -> Optional[dict[str, Any]]:
    """Возвращает ``dict`` или ``None`` (раньше возвращал ``{}``)."""
    with Database(db_path) as conn:
        repo = UserRepository(conn)
        return repo.get_user_by_name(name)


def store_password(user_id: int, password: str) -> str:
    """Сохраняет bcrypt-хеш пароля; возвращает хеш."""
    return _passwords.store(int(user_id), password)


def verify_password(user_id: int, password: str) -> bool:
    """Проверяет пароль по сохранённому хешу."""
    hashed = _passwords.find_hash(int(user_id))
    return bool(hashed) and _passwords.verify(password, hashed)


def set_active(user_id: int) -> None:
    """Регистрирует пользователя как активного (потокобезопасно)."""
    _active.add(user_id)


def get_active_users() -> list[int]:
    """Возвращает снимок активных пользователей."""
    return _active.snapshot()


__all__ = [
    "add_user",
    "get_user_by_name",
    "store_password",
    "verify_password",
    "set_active",
    "get_active_users",
]
