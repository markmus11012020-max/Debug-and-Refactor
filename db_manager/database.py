"""Модуль управления соединением с SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Optional, Type


class Database:
    """Контекст-менеджер для безопасной работы с SQLite-соединением.

    Гарантирует закрытие соединения даже при исключениях и предоставляет
    единое место для инициализации схемы БД.
    """

    def __init__(self, db_path: str | Path = "users.db") -> None:
        self._db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = sqlite3.connect(str(self._db_path))
        # Включаем поддержку внешних ключей и Row-фабрику для удобства.
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema(self._conn)
        return self._conn

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self._conn is not None:
            try:
                if exc_type is None:
                    self._conn.commit()
                else:
                    self._conn.rollback()
            finally:
                self._conn.close()
                self._conn = None

    @staticmethod
    def _ensure_schema(conn: sqlite3.Connection) -> None:
        """Создаёт таблицы, если их ещё нет."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                tags TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        conn.commit()