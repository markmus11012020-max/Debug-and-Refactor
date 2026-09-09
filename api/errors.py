"""Централизованные обработчики ошибок HTTP API."""

from __future__ import annotations

import sqlite3

import flask
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Базовое исключение API с HTTP-кодом."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class NotFoundError(APIError):
    def __init__(self, message: str = "not found") -> None:
        super().__init__(message, status=404)


class ValidationError(APIError):
    def __init__(self, message: str = "invalid request") -> None:
        super().__init__(message, status=422)


class ConflictError(APIError):
    def __init__(self, message: str = "conflict") -> None:
        super().__init__(message, status=409)


def register_error_handlers(app: flask.Flask) -> None:
    @app.errorhandler(APIError)
    def _handle_api_error(err: APIError):
        return flask.jsonify({"error": err.message}), err.status

    @app.errorhandler(sqlite3.IntegrityError)
    def _handle_integrity_error(err: sqlite3.IntegrityError):
        return flask.jsonify({"error": "database integrity error"}), 409

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err: HTTPException):
        return (
            flask.jsonify({"error": err.description or err.name}),
            err.code or 500,
        )

    @app.errorhandler(Exception)
    def _handle_unexpected(err: Exception):
        app.logger.exception("Unhandled error: %s", err)
        return flask.jsonify({"error": "internal server error"}), 500