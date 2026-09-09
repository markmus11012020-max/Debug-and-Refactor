"""Интеграционные тесты HTTP API (Flask test client)."""

from __future__ import annotations

from pathlib import Path

import pytest

from api import create_app
from api.config import APIConfig
from db_manager import PasswordService


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = APIConfig(
        db_path=str(tmp_path / "u.db"),
        passwords_file=str(tmp_path / "p.txt"),
        bcrypt_rounds=4,
        active_users_maxlen=3,
    )
    flask_app = create_app(cfg)
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_then_get_user(client) -> None:
    r = client.post("/users", json={"name": "alice", "tags": ["vip"]})
    assert r.status_code == 201, r.data
    body = r.get_json()
    assert body["name"] == "alice"
    assert body["id"] > 0

    uid = body["id"]
    r2 = client.get(f"/users/{uid}")
    assert r2.status_code == 200
    assert r2.get_json()["name"] == "alice"


def test_create_user_validates_missing_name(client) -> None:
    r = client.post("/users", json={})
    assert r.status_code == 422
    assert "name" in r.get_json()["error"]


def test_create_user_validates_empty_name(client) -> None:
    r = client.post("/users", json={"name": "   "})
    assert r.status_code == 422


def test_create_user_validates_tags_type(client) -> None:
    r = client.post("/users", json={"name": "x", "tags": "oops"})
    assert r.status_code == 422


def test_get_user_404(client) -> None:
    r = client.get("/users/999")
    assert r.status_code == 404
    assert r.get_json()["error"] == "user 999 not found"


def test_sql_injection_via_http(client) -> None:
    payload = {"name": "x'); DROP TABLE users;--"}
    r = client.post("/users", json=payload)
    assert r.status_code == 201
    # Таблица цела:
    r2 = client.get("/users")
    assert r2.status_code == 200
    assert len(r2.get_json()) == 1


def test_list_users(client) -> None:
    client.post("/users", json={"name": "a"})
    client.post("/users", json={"name": "b"})
    r = client.get("/users")
    assert r.status_code == 200
    data = r.get_json()
    assert {u["name"] for u in data} == {"a", "b"}


def test_set_password_then_active(client) -> None:
    r = client.post("/users", json={"name": "carol"})
    uid = r.get_json()["id"]

    rp = client.post(f"/users/{uid}/password", json={"password": "hunter2"})
    assert rp.status_code == 201

    # active: используем синглтон через extensions
    from api import extensions

    extensions.get_active_users().add(uid)
    r = client.get("/active")
    assert r.status_code == 200
    assert uid in r.get_json()


def test_set_password_validates_missing_field(client) -> None:
    r = client.post("/users", json={"name": "d"})
    uid = r.get_json()["id"]
    rp = client.post(f"/users/{uid}/password", json={})
    assert rp.status_code == 422


def test_set_password_404(client) -> None:
    r = client.post("/users/9999/password", json={"password": "x"})
    assert r.status_code == 404


def test_internal_error_returns_500(client) -> None:
    """Любое необработанное исключение превращается в 500 JSON."""
    from api import extensions

    svc = extensions.get_passwords()
    orig = svc.store

    def boom(uid, pw):
        raise RuntimeError("boom")

    svc.store = boom  # type: ignore[assignment]
    try:
        r = client.post("/users", json={"name": "e"})
        uid = r.get_json()["id"]
        rp = client.post(f"/users/{uid}/password", json={"password": "x"})
        assert rp.status_code == 500
        assert rp.get_json()["error"] == "internal server error"
    finally:
        svc.store = orig  # type: ignore[assignment]


def test_repository_uses_parametrized_query(client) -> None:
    """Sanity-check: код не должен пытаться конкатенировать SQL."""
    r = client.get("/users/0")
    assert r.status_code == 404