# Debug and Refactor — db_manager

Рефакторинг исходного `utils.py` в пакетную OOP-архитектуру с
потокобезопасностью, безопасным хранением паролей (bcrypt) и параметризованными
SQL-запросами.

## Структура проекта

```
Debug and Refactor/
├── db_manager/                 # основной пакет
│   ├── __init__.py             # публичный API
│   ├── database.py             # Database — контекст-менеджер для SQLite
│   ├── user_repository.py      # UserRepository — CRUD пользователей
│   ├── password_service.py     # PasswordService — bcrypt + потокобезопасный файл
│   └── active_users.py         # ActiveUsers — потокобезопасная очередь
├── tests/
│   └── test_db_manager.py      # 14 тестов (pytest)
├── utils.py                    # обратно-совместимый фасад
├── requirements.txt
├── .env.example
├── start.bat                   # авто-деплой: stop → clean → install → test
└── README.md
```

## Что исправлено относительно исходного `utils.py`

| Проблема                                            | Решение                                                |
| --------------------------------------------------- | ------------------------------------------------------ |
| SQL-инъекция в `add_user` и `get_user_by_name`      | Параметризованные запросы через `?`-плейсхолдеры       |
| Соединение SQLite не закрывалось при ошибке         | `Database` как контекст-менеджер с `commit/rollback`   |
| `tags=[]` мутируемый аргумент по умолчанию          | `tags=None` + `list(tags)` внутри функции              |
| Возврат `str` вместо `int` id                       | `return int(cur.lastrowid)`                            |
| "Хеш" пароля через `password[::-1]`                 | `bcrypt.hashpw` + `bcrypt.gensalt(rounds=12)`          |
| Файл паролей не закрывался                          | `with self._path.open(...) as fh`                      |
| Race condition в `active_users`                     | `threading.Lock` + `collections.deque(maxlen=...)`     |
| `get_user_by_name` возвращал `{}` для отсутствующих | Возвращает `None` (контракт соблюдён)                  |
| Дублирование функции в файле                        | Удалено; единая реализация в `password_service.py`     |
| Всё в одном файле                                   | Разделение на пакет с единственной ответственностью    |

## Установка и запуск

```bash
pip install -r requirements.txt
start.bat            # Windows: stop → clean → install → test
```

Или вручную:

```bash
python -m pytest tests -q
```

## Использование

```python
import utils

uid = utils.add_user("alice", tags=["vip"])     # int
utils.store_password(uid, "s3cret!")            # bcrypt-хеш в passwords.txt
assert utils.verify_password(uid, "s3cret!") is True

utils.set_active(uid)
print(utils.get_active_users())
```

## Конфигурация (`.env.example`)

```
DB_PATH=users.db
PASSWORDS_FILE=passwords.txt
BCRYPT_ROUNDS=12
ACTIVE_USERS_MAXLEN=5
LLM_BASE_URL=https://api.aitunnel.ru/v1
LLM_MODEL=minimax-m3
```

## Тесты

```
$ python -m pytest tests -q
..............                                  [100%]
14 passed in 0.51s
```

Покрытие: thread-safety, валидация, SQL-инъекции, корректность JSON,
bcrypt round-trip, фасад `utils.py`.