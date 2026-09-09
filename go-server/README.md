# Go-Server — порт db_manager + HTTP API на Golang

Полностью функциональный порт исходного Python-проекта (`Debug and Refactor`)
на язык **Go**. Сохранены:

* доменный слой — `SQLiteStore` (`users`), `PasswordStore` (bcrypt), `ActiveUsers`;
* HTTP API — те же эндпоинты и коды ответов, что и у Flask-версии;
* структура проекта (OOP-подход: один пакет — одна ответственность);
* запуск одной командой `start.bat` (stop → clean → build → test → run).

## Структура

```
go-server/
├── cmd/server/main.go          # точка входа + graceful shutdown
├── internal/
│   ├── api/
│   │   ├── server.go           # маршруты + handlers
│   │   ├── middleware.go       # logging + recoverer
│   │   └── errors.go           # APIError + JSON helpers
│   ├── config/config.go        # конфигурация из ENV
│   ├── domain/models.go        # User + доменные ошибки
│   └── store/
│       ├── sqlite.go           # SQLite (modernc.org/sqlite, без CGO)
│       ├── passwords.go        # bcrypt + потокобезопасный файл
│       └── active.go           # ограниченный LIFO-список user_id
├── tests/handlers_test.go      # httptest-тесты
├── docs/openapi.yaml           # OpenAPI 3.1 спецификация API
├── go.mod / go.sum
├── .env.example
├── start.bat                   # авто-деплой (Windows)
└── README.md
```

## Сравнение с Python-версией

| Возможность                       | Python (Flask)     | Go (net/http)              |
| --------------------------------- | ------------------ | -------------------------- |
| БД                                | sqlite3            | modernc.org/sqlite (pure)  |
| Хеши паролей                      | bcrypt             | golang.org/x/crypto/bcrypt |
| Потокобезопасность                | threading.Lock     | sync.Mutex                 |
| Валидация                         | ручной словарь     | ручной парсер JSON         |
| HTTP-роутер                       | Flask Blueprint    | net/http + ServeMux        |
| Остановка старых процессов        | wmic python.exe    | wmic go-server.exe         |
| Кэш-очистка                       | __pycache__/*.pyc  | удаление bin/ и *.exe      |
| Сборка                            | pip install        | go mod tidy + go build     |
| Тесты                             | pytest             | go test                    |

## Эндпоинты

| Метод | Путь                          | Код | Описание                       |
| ----- | ----------------------------- | --- | ------------------------------ |
| GET   | `/health`                     | 200 | healthcheck                    |
| POST  | `/users`                      | 201 | создать пользователя           |
| GET   | `/users`                      | 200 | список пользователей           |
| GET   | `/users/<id>`                 | 200 / 404 | получить пользователя   |
| POST  | `/users/<id>/password`        | 201 / 404 | сохранить bcrypt-хеш     |
| GET   | `/active`                     | 200 | активные пользователи          |

### Примеры

```bash
curl -X POST http://127.0.0.1:5000/users \
     -H "Content-Type: application/json" \
     -d '{"name":"alice","tags":["vip"]}'

curl http://127.0.0.1:5000/users/1

curl -X POST http://127.0.0.1:5000/users/1/password \
     -H "Content-Type: application/json" \
     -d '{"password":"hunter2"}'

curl http://127.0.0.1:5000/active
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

Переменные читаются напрямую из ENV. На Windows их удобно прописывать через
`setx KEY=value` либо передавать перед запуском:

```cmd
set API_PORT=8080 && bin\go-server.exe
```

## Установка и запуск

### Требования

* Go ≥ 1.22 ([https://go.dev/dl/](https://go.dev/dl/))

### Быстрый старт (Windows)

```cmd
git clone <repo>
cd Debug-and-Refactor/go-server
start.bat
```

Скрипт автоматически:

1. останавливает предыдущие `go-server.exe`;
2. удаляет `bin/`, `*.exe`, кэш сборки;
3. выполняет `go mod tidy` и `go build -o bin\go-server.exe ./cmd/server`;
4. запускает `go test ./tests/...`;
5. запускает `bin\go-server.exe`.

### Запуск вручную (кросс-платформенно)

```bash
go mod tidy
go build -o bin/go-server ./cmd/server
go test ./tests/...
./bin/go-server         # Linux/macOS
bin\go-server.exe       # Windows
```

## Архитектурные принципы

* **Разделение ответственности**: `store` не знает про HTTP, `api` не знает про SQL.
* **Инкапсуляция**: всё состояние (`sync.Mutex`, `bcrypt.Cost`, `*sql.DB`) скрыто в полях соответствующих типов.
* **Масштабируемость**:
  * `Server` принимает интерфейс хранилища в конструкторе — можно подменить на PostgreSQL/Redis/etc.;
  * middleware подключаются через `chain(handler, mws...)`;
  * все размеры и стоимости bcrypt параметризованы через ENV.
* **Безопасность**:
  * параметризованные SQL-запросы (`?`) — нет инъекций;
  * bcrypt-хеши вместо открытых паролей;
  * лимит на длину имени/тегов и количество тегов.
* **Graceful shutdown**: `SIGINT`/`SIGTERM` → `httpSrv.Shutdown(ctx)`.

## Тесты

```
go test ./tests/... -v
```

Покрывают: healthcheck, CRUD, 404, 422, потокобезопасность LLM-модели
активных пользователей, отсутствие уязвимости к SQL-инъекциям.

## OpenAPI 3.1

Полная спецификация API лежит в [`docs/openapi.yaml`](docs/openapi.yaml).
Покрывает все эндпоинты (`/health`, `/users`, `/users/{user_id}`,
`/users/{user_id}/password`, `/active`), схемы (`User`, `UserCreate`,
`PasswordCreate`, `PasswordStored`, `ApiError`, `Health`) и единые
ответы ошибок `400/404/422/500`. Используется для генерации клиентов,
тестов через Schemathesis и валидации контракта.

```bash
# Просмотр через Swagger UI / Redoc — откройте docs/openapi.yaml в редакторе
# или разверните локально через swagger-ui-cli.
```

## Расширение проекта

* `LLM_BASE_URL=https://api.aitunnel.ru/v1` и `LLM_MODEL=minimax-m3`
  зарезервированы для подключения LLM-слоя (например, в `internal/llm/`).
* Для прод-нагрузок SQLite можно заменить на PostgreSQL: реализовать
  тот же интерфейс методов `AddUser/GetByID/List/...` и передать
  его в `api.NewServer(...)`.