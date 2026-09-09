"""HTTP API поверх пакета ``db_manager``.

Структура пакета:
    api/
    ├── __init__.py        # create_app — фабрика Flask-приложения
    ├── config.py          # APIConfig — чтение .env / переменных окружения
    ├── extensions.py      # синглтоны сервисов + per-request соединение
    ├── errors.py          # централизованные обработчики ошибок
    ├── schemas.py         # валидация входящих JSON (без внешних зависимостей)
    └── routes.py          # Blueprint с эндпоинтами /users, /health
"""

from __future__ import annotations

from .factory import create_app

__all__ = ["create_app"]
__version__ = "1.0.0"