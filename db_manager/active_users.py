"""Потокобезопасный список активных пользователей."""

from __future__ import annotations

import threading
from collections import deque
from typing import Deque, Iterable, List


class ActiveUsers:
    """Потокобезопасная очередь активных пользователей с ограничением длины.

    Заменяет глобальный список + ручной ``time.sleep`` + логику ``pop(0)``:
    теперь всё под защитой ``threading.Lock``, а размер ограничен
    атрибутом ``maxlen``.
    """

    def __init__(self, maxlen: int = 5) -> None:
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self._users: Deque[int] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, user_id: int) -> None:
        """Добавляет пользователя, удаляя самый старый при переполнении."""
        with self._lock:
            self._users.append(int(user_id))

    def snapshot(self) -> List[int]:
        """Возвращает копию текущего списка активных пользователей."""
        with self._lock:
            return list(self._users)

    def clear(self) -> None:
        """Очищает список."""
        with self._lock:
            self._users.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._users)

    def __iter__(self) -> Iterable[int]:
        # Итерация по копии — безопасно даже при модификации из других потоков.
        return iter(self.snapshot())