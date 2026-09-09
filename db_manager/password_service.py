"""Сервис безопасного хранения паролей через bcrypt."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Union

import bcrypt


class PasswordService:
    """Хеширование и проверка паролей с использованием bcrypt.

    Файл ``passwords.txt`` хранит записи вида ``user_id:bcrypt_hash``.
    Запись и чтение файла защищены ``threading.Lock`` для потокобезопасности.
    """

    def __init__(
        self,
        storage_path: Union[str, Path] = "passwords.txt",
        rounds: int = 12,
    ) -> None:
        self._path = Path(storage_path)
        self._rounds = rounds
        self._lock = threading.Lock()

    def hash_password(self, password: str) -> str:
        """Возвращает bcrypt-хеш пароля (строка)."""
        if not isinstance(password, str) or not password:
            raise ValueError("password must be a non-empty string")
        salt = bcrypt.gensalt(rounds=self._rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """Проверяет соответствие пароля хешу."""
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    def store(self, user_id: int, password: str) -> str:
        """Сохраняет пароль пользователя и возвращает хеш."""
        hashed = self.hash_password(password)
        line = f"{int(user_id)}:{hashed}\n"
        with self._lock:
            # Открываем в режиме append с явной кодировкой;
            # контекст-менеджер гарантирует закрытие даже при ошибке.
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        return hashed

    def find_hash(self, user_id: int) -> str | None:
        """Ищет сохранённый хеш по user_id. Возвращает ``None``, если не найден."""
        target = f"{int(user_id)}:"
        with self._lock:
            if not self._path.exists():
                return None
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith(target):
                        return line.rstrip("\n").split(":", 1)[1]
        return None