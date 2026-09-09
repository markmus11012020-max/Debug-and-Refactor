# Debug and Refactor — db_manager + HTTP API

Рефакторинг исходного `utils.py` и битого `api.py` в пакетную OOP-архитектуру с
потокобезопасностью, безопасным хранением паролей (bcrypt), параметризованными
SQL-запросами и масштабируемым Flask-слоем.

## Структура проекта

```
Debug and Refactor/
├── db_manager/                 # доменный слой
│   ├── __init__.py
│   ├── database.py             # Database — контекст-менеджер для SQLite
│   ├── user_repository.py      # UserRepository — CRUD пользователей
│   ├── password_service.py     # PasswordService — bcrypt + потокобезопасный файл
│   └── active_users.py         # ActiveUsers — потокобезопасная очередь
├── api/                        # транспортный слой (Flask)
│   ├── __init__.py             # create_app
│   ├── factory.py              # фабрика приложения
│   ├── config.py               # APIConfig — dataclass из env
│   ├── extensions.py           # синглтоны + per-request DB
│   ├── errors.py               # APIError + обработчики
│   ├── schemas.py              # валидация JSON
│   └── routes.py               # Blueprint /health, /users, /active
├── tests/
│   ├── test_db_manager.py      # 14 тестов доменного слоя
│   └── test_api.py             # 12 тестов HTTP-слоя
├── utils.py                    # обратно-совместимый фасад
├── wsgi.py                     # точка входа для запуска API
├── requirements.txt
├── .env.example
├── start.bat                   # авто-деплой + тесты + запуск
└── README.md
```

## Что исправлено относительно битого `api.py`

| Проблема                                           | Решение                                          |
| -------------------------------------------------- | ------------------------------------------------ |
| `sqlite3.conn@ct(...)` — синтаксическая ошибка     | `Database(db_path)` контекст-менеджер            |
| `methods=["POST")` — лишняя скобка                 | `methods=["POST"]` (валидный список)             |
| `fINSERT ... VALUES('{name}')` — f-string +инъекция| Параметризованные запросы `?`                     |
| `select id,name from users where id="+uid` —инъекция | Параметризованные запросы в `UserRepository`    |
| Глобальный `conn` (race conditions)                | Per-request соединение через `flask.g`            |
| `return jsonify({...}))` — лишняя скобка           | `return flask.jsonify(...), status`              |
| Статус `201` на чтение                             | `GET` возвращает `200`, `POST` — `201`           |
| `app.route("/user/<uid>")` без указания типа       | `/users/<int:user_id>` + Blueprint               |
| Нет валидации входа                                | `schemas.validate_create_user`                   |
| Нет обработки ошибок                              | `errors.register_error_handlers` → JSON-ответы   |
| Всё в одном файле                                  | Пакет `api/` с фабрикой, blueprints, сервисами   |

## Эндпоинты API

| Метод  | Путь                              | Описание                          |
| ------ | --------------------------------- | --------------------------------- |
| GET    | `/health`                         | healthcheck                        |
| POST   | `/users`                          | создать пользователя              |
| GET    | `/users`                          | список пользователей              |
| GET    | `/users/<id>`                     | получить пользователя              |
| POST   | `/users/<id>/password`            | сохранить bcrypt-хеш пароля        |
| GET    | `/active`                         | активные пользователи             |

Примеры:

```bash
curl -X POST http://127.0.0.1:5000/users -H "Content-Type: application/json" \
     -d '{"name":"alice","tags":["vip"]}'
curl http://127.0.0.1:5000/users/1
curl -X POST http://127.0.0.1:5000/users/1/password -H "Content-Type: application/json" \
     -d '{"password":"hunter2"}'
curl http://127.0.0.1:5000/active
```

## Установка и запуск

```bash
pip install -r requirements.txt
start.bat            # Windows: stop → clean → install → test → run API
```

Или вручную:

```bash
python -m pytest tests -q
python wsgi.py
```

## Конфигурация (`.env.example`)

```
DB_PATH=users.db
PASSWORDS_FILE=passwords.txt
BCRYPT_ROUNDS=12
ACTIVE_USERS_MAXLEN=5
API_HOST=127.0.0.1
API_PORT=5000
API_DEBUG=0
LLM_BASE_URL=https://api.aitunnel.ru/v1
LLM_MODEL=minimax-m3
```

## Тесты

```
$ python -m pytest tests -q
..................                                  [100%]
26 passed
```

Покрытие: thread-safety, валидация, SQL-инъекции, bcrypt round-trip,
HTTP-коды, фасад `utils.py`, фабрика Flask.