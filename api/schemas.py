"""Минимальная валидация входящих JSON-данных.

Используется только стандартная библиотека, чтобы не добавлять лишних
зависимостей. Для крупного проекта стоит заменить на marshmallow/pydantic.
"""

from __future__ import annotations

from typing import Any

from .errors import ValidationError

MAX_NAME_LEN = 64
MAX_TAGS = 16
MAX_TAG_LEN = 32


def _require_json(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("request body must be a JSON object")
    return payload


def validate_create_user(payload: Any) -> tuple[str, list[str] | None]:
    """Возвращает ``(name, tags_or_None)``."""
    data = _require_json(payload)
    if "name" not in data:
        raise ValidationError("'name' is required")

    name = data["name"]
    if not isinstance(name, str):
        raise ValidationError("'name' must be a string")
    name = name.strip()
    if not name:
        raise ValidationError("'name' must not be empty")
    if len(name) > MAX_NAME_LEN:
        raise ValidationError(f"'name' length must be <= {MAX_NAME_LEN}")

    tags_raw = data.get("tags")
    tags: list[str] | None = None
    if tags_raw is not None:
        if not isinstance(tags_raw, list):
            raise ValidationError("'tags' must be a list of strings")
        if len(tags_raw) > MAX_TAGS:
            raise ValidationError(f"too many tags (max {MAX_TAGS})")
        tags = []
        for i, t in enumerate(tags_raw):
            if not isinstance(t, str):
                raise ValidationError(f"tag #{i} must be a string")
            t = t.strip()
            if not t:
                raise ValidationError(f"tag #{i} must not be empty")
            if len(t) > MAX_TAG_LEN:
                raise ValidationError(f"tag #{i} too long (max {MAX_TAG_LEN})")
            tags.append(t)
    return name, tags