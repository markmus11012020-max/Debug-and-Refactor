"""Репозиторий пользователей: безопасный CRUD поверх SQLite."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


class UserRepository:
    """Инкапсулирует все запросы к таблице `users`.

    Все методы принимают уже открытое соединение, что упрощает
    композицию с контекст-менеджером Database и транзакциями.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_user(self, name: str, tags: Optional[list[str]] = None) -> int:
        """Добавляет пользователя. Возвращает целочисленный id.

        Тег ``"new"`` добавляется к копии списка, оригинал не мутируется.
        """
        # Работаем с копией, чтобы не модифицировать аргумент вызывающего.
        tags = list(tags) if tags else []
        tags.append("new")

        cur = self._conn.execute(
            "INSERT INTO users (name, tags) VALUES (?, ?)",
            (name, json.dumps(tags)),
        )
        return int(cur.lastrowid)

    def get_user_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Возвращает пользователя по имени или ``None``.

        Теги десериализуются безопасно; при повреждённом JSON —
        возвращается ``None`` (контракт: либо валитный dict, либо None).
        """
        cur = self._conn.execute(
            "SELECT id, name, tags FROM users WHERE name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        try:
            tags = json.loads(row["tags"])
        except (TypeError, ValueError):
            return None
        return {"id": int(row["id"]), "name": row["name"], "tags": tags}

    def delete_by_name(self, name: str) -> int:
        """Удаляет пользователя; возвращает количество удалённых строк."""
        cur = self._conn.execute("DELETE FROM users WHERE name = ?", (name,))
        return cur.rowcount

    def get_user_by_id(self, user_id: int) -> Optional[dict[str, Any]]:
        """Возвращает пользователя по ``id`` или ``None``.

        Используется HTTP-слоем для эндпоинта ``GET /users/<id>``.
        Параметризованный запрос — безопасен от SQL-инъекций.
        """
        cur = self._conn.execute(
            "SELECT id, name, tags FROM users WHERE id = ?",
            (int(user_id),),
        )
        row = cur.fetchone()
        if row is None:
            return None
        try:
            tags = json.loads(row["tags"])
        except (TypeError, ValueError):
            tags = []
        return {"id": int(row["id"]), "name": row["name"], "tags": tags}

    def list_users(self) -> list[dict[str, Any]]:
        """Возвращает всех пользователей, упорядоченных по ``id``."""
        rows = self._conn.execute(
            "SELECT id, name, tags FROM users ORDER BY id"
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                tags = json.loads(row["tags"])
            except (TypeError, ValueError):
                tags = []
            out.append({"id": int(row["id"]), "name": row["name"], "tags": tags})
        return out