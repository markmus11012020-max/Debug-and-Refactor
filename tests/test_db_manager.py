"""Тесты пакета db_manager и обратно-совместимого utils.py."""

from __future__ import annotations

import os
import threading
import tempfile
from pathlib import Path

import pytest

from db_manager import (
    ActiveUsers,
    Database,
    PasswordService,
    UserRepository,
)
import utils


# ---------- ActiveUsers ----------

def test_active_users_is_thread_safe() -> None:
    au = ActiveUsers(maxlen=3)
    threads = []

    def worker(start: int) -> None:
        for i in range(start, start + 100):
            au.add(i)

    for t in range(8):
        th = threading.Thread(target=worker, args=(t * 100,))
        threads.append(th)
        th.start()
    for th in threads:
        th.join()

    # Размер ограничен maxlen=3, и не потеряли данные при гонках.
    assert len(au) == 3
    # snapshot возвращает копию — изменения снаружи не влияют на внутренности.
    snap = au.snapshot()
    snap.append(99999)
    assert len(au) == 3


def test_active_users_maxlen_validation() -> None:
    with pytest.raises(ValueError):
        ActiveUsers(maxlen=0)


# ---------- UserRepository ----------

def _make_repo() -> tuple[UserRepository, Database, Path]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)

    class _Ctx:
        def __enter__(self):
            self._db = Database(path)
            return self._db.__enter__()

        def __exit__(self, *exc):
            return self._db.__exit__(*exc)

    # используем Database как CM
    return None, db, Path(path)


def test_add_user_returns_int_and_does_not_mutate_input() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "u.db"
        with Database(db_path) as conn:
            repo = UserRepository(conn)
            tags = ["vip"]
            uid = repo.add_user("alice", tags)
            assert isinstance(uid, int)
            assert uid > 0
            assert tags == ["vip"], "оригинальный tags не должен мутироваться"


def test_add_user_appends_new_tag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "u.db"
        with Database(db_path) as conn:
            repo = UserRepository(conn)
            uid = repo.add_user("bob")
            user = repo.get_user_by_name("bob")
            assert user is not None
            assert user["id"] == uid
            assert user["name"] == "bob"
            assert user["tags"] == ["new"]


def test_get_user_by_name_returns_none_for_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "u.db"
        with Database(db_path) as conn:
            repo = UserRepository(conn)
            assert repo.get_user_by_name("ghost") is None


def test_get_user_by_name_handles_corrupted_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "u.db"
        with Database(db_path) as conn:
            conn.execute(
                "INSERT INTO users (name, tags) VALUES (?, ?)",
                ("eve", "not-a-json"),
            )
            conn.commit()
            repo = UserRepository(conn)
            assert repo.get_user_by_name("eve") is None


def test_sql_injection_is_neutralized() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "u.db"
        with Database(db_path) as conn:
            repo = UserRepository(conn)
            # Попытка инъекции — должна быть сохранена как обычная строка.
            malicious = "x'); DROP TABLE users;--"
            repo.add_user(malicious)
            # Таблица всё ещё существует и доступна.
            cur = conn.execute("SELECT COUNT(*) AS c FROM users")
            assert cur.fetchone()["c"] == 1
            # Поиск по части инъекции не должен находить других пользователей.
            assert repo.get_user_by_name("alice") is None


# ---------- PasswordService ----------

def test_password_hash_and_verify_roundtrip(tmp_path: Path) -> None:
    svc = PasswordService(storage_path=tmp_path / "p.txt", rounds=4)
    hashed = svc.store(1, "s3cret!")
    assert hashed != "s3cret!"
    assert hashed != "!terc3s"  # не реверс
    assert svc.verify("s3cret!", hashed) is True
    assert svc.verify("wrong", hashed) is False


def test_password_service_validates_empty(tmp_path: Path) -> None:
    svc = PasswordService(storage_path=tmp_path / "p.txt", rounds=4)
    with pytest.raises(ValueError):
        svc.store(1, "")


def test_find_hash_returns_none_when_missing(tmp_path: Path) -> None:
    svc = PasswordService(storage_path=tmp_path / "missing.txt", rounds=4)
    assert svc.find_hash(42) is None


# ---------- utils.py фасад ----------

def test_utils_add_and_get(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "users.db"
    # utils использует синглтоны PasswordService; меняем путь только для БД.
    uid = utils.add_user("alice", tags=["vip"], db_path=str(db_file))
    assert isinstance(uid, int)
    user = utils.get_user_by_name("alice", db_path=str(db_file))
    assert user is not None
    assert user["name"] == "alice"
    assert user["tags"] == ["vip", "new"]


def test_utils_get_missing_returns_none(tmp_path: Path) -> None:
    db_file = tmp_path / "users.db"
    assert utils.get_user_by_name("nobody", db_path=str(db_file)) is None


def test_utils_active_users_roundtrip() -> None:
    for i in range(20):
        utils.set_active(i)
    snap = utils.get_active_users()
    # синглтон ActiveUsers(maxlen=5)
    assert len(snap) == 5
    assert snap == [15, 16, 17, 18, 19]


def test_utils_verify_password_roundtrip(tmp_path: Path) -> None:
    # Меняем путь к файлу паролей через monkeypatch на уровне модуля.
    pwd_file = tmp_path / "pw.txt"
    monkey = pytest.MonkeyPatch()
    monkey.setattr(utils, "_passwords", PasswordService(pwd_file, rounds=4))
    utils.store_password(7, "hello-world")
    assert utils.verify_password(7, "hello-world") is True
    assert utils.verify_password(7, "no") is False
    monkey.undo()