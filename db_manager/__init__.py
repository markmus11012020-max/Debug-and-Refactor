"""db_manager — пакет для безопасной работы с пользователями и паролями.

Публичный API:
    Database        — менеджер соединения с SQLite (контекст-менеджер).
    UserRepository  — CRUD по таблице users (параметризованные запросы).
    PasswordService — хеширование/проверка паролей через bcrypt.
    ActiveUsers     — потокобезопасный список активных пользователей.
"""

from .database import Database
from .user_repository import UserRepository
from .password_service import PasswordService
from .active_users import ActiveUsers

__all__ = [
    "Database",
    "UserRepository",
    "PasswordService",
    "ActiveUsers",
]

__version__ = "1.0.0"