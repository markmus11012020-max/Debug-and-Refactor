"""Фабрика Flask-приложения."""

from __future__ import annotations

import flask

from .config import APIConfig
from .errors import register_error_handlers
from .extensions import close_db, init_extensions
from .routes import bp as api_bp


def create_app(cfg: APIConfig | None = None) -> flask.Flask:
    """Создаёт и настраивает Flask-приложение.

    Параметр ``cfg`` позволяет подменить конфиг в тестах.
    """
    app = flask.Flask(__name__)
    cfg = cfg or APIConfig.from_env()

    init_extensions(app, cfg)
    register_error_handlers(app)

    app.register_blueprint(api_bp)
    app.teardown_appcontext(close_db)
    return app