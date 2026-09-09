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

---

## 🐳 Docker — локальный запуск и публикация на Docker Hub

В репозитории лежат:

| Файл                          | Назначение                                                  |
| ----------------------------- | ----------------------------------------------------------- |
| `Dockerfile`                  | Мульти-сборка: target `python` (Flask) и target `go` (default, distroless) |
| `docker-compose.yml`          | Поднимает один из сервисов через `profiles`                 |
| `.dockerignore`               | Исключает мусор из контекста сборки                         |
| `scripts/test_endpoints.sh`   | Проверка всех эндпоинтов через `curl` (Linux/macOS/Git-Bash)|
| `scripts/test_endpoints.bat`  | То же для Windows `cmd.exe`                                 |

### 1. Сборка и запуск **локально** (без Docker Hub)

```bash
# Python-версия
docker build --target python -t debug-refactor:py .
docker run --rm -p 5000:5000 -v py_data:/data debug-refactor:py

# Go-версия (по умолчанию)
docker build -t debug-refactor:go .
docker run --rm -p 5000:5000 -v go_data:/data debug-refactor:go
```

Или через Compose:

```bash
docker compose --profile python up --build      # Flask
docker compose --profile go     up --build      # Go (default)
```

В обоих случаях API слушает `http://127.0.0.1:5000`. Данные
пользователей и bcrypt-файл лежат в Docker-volume `py_data`/`go_data`.

### 2. Проверка эндпоинтов

```bash
# Linux / macOS / Git-Bash
./scripts/test_endpoints.sh

# Windows cmd.exe
scripts\test_endpoints.bat

# Удалённый сервер
BASE_URL=http://my-server:5000 ./scripts/test_endpoints.sh
```

Скрипт проходит 13 кейсов (health, create, get, list, set-password,
active, edge-cases) и печатает `OK / FAIL` для каждого.

### 3. Публикация на Docker Hub

#### 3.1. Подготовка аккаунта

```bash
# Регистрация (если нет): https://hub.docker.com/signup
docker login
# введите логин и пароль; для 2FA — Personal Access Token
```

> В примерах ниже используется namespace `markmus11012020` и репозиторий
> `debug-refactor` (поменяйте на свой, если нужно).

#### 3.2. Тег образов

```bash
# Go (default)
docker build -t markmus11012020/debug-refactor:go-1.0.0 .
docker build --target go -t markmus11012020/debug-refactor:go \
                                 -t markmus11012020/debug-refactor:latest .

# Python
docker build --target python \
  -t markmus11012020/debug-refactor:py-1.0.0 \
  -t markmus11012020/debug-refactor:py .
```

#### 3.3. Push

```bash
docker push markmus11012020/debug-refactor:go-1.0.0
docker push markmus11012020/debug-refactor:go
docker push markmus11012020/debug-refactor:py-1.0.0
docker push markmus11012020/debug-refactor:py
```

Проверить, что образ доступен:
https://hub.docker.com/r/markmus11012020/debug-refactor/tags

#### 3.4. Автоматизация через GitHub Actions (опционально)

Файл `.github/workflows/docker-publish.yml`:

```yaml
name: docker-publish
on:
  push:
    tags: ["v*.*.*"]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Build & push (go)
        uses: docker/build-push-action@v5
        with:
          context: .
          target: go
          push: true
          tags: |
            markmus11012020/debug-refactor:go-${{ github.ref_name }}
            markmus11012020/debug-refactor:latest
      - name: Build & push (py)
        uses: docker/build-push-action@v5
        with:
          context: .
          target: python
          push: true
          tags: markmus11012020/debug-refactor:py-${{ github.ref_name }}
```

Секреты `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` добавляются в
Settings → Secrets → Actions репозитория.

---

## 🚀 Запуск на сервере (пошагово)

### Шаг 1. Подключение к серверу

```bash
ssh user@my-server
```

### Шаг 2. Установка Docker (если ещё нет)

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

### Шаг 3. Создание рабочей директории

```bash
mkdir -p ~/debug-refactor && cd ~/debug-refactor
```

### Шаг 4. Подготовка файлов на сервере

На сервере нужны **только** эти файлы (всё остальное — внутри образа):

```bash
# Вариант А — клонировать репозиторий
git clone https://github.com/markmus11012020-max/Debug-and-Refactor.git .
git checkout main

# Вариант Б — скачать только нужные файлы вручную
nano docker-compose.yml   # вставить содержимое из репозитория
mkdir -p scripts
nano scripts/test_endpoints.sh
chmod +x scripts/test_endpoints.sh
```

`docker-compose.yml` рекомендуется адаптировать под прод:

```yaml
services:
  api-go:
    image: markmus11012020/debug-refactor:go-1.0.0   # зафиксированный тег
    container_name: debug-refactor-go
    restart: unless-stopped
    ports:
      - "80:5000"          # отдаём наружу на 80-м порту
    environment:
      DB_PATH: /data/users.db
      PASSWORDS_FILE: /data/passwords.txt
      BCRYPT_ROUNDS: "12"
      ACTIVE_USERS_MAXLEN: "5"
      API_HOST: 0.0.0.0
      API_PORT: "5000"
    volumes:
      - go_data:/data       # данные переживают перезапуск контейнера
volumes:
  go_data:
```

### Шаг 5. Запуск

```bash
# Если compose-файл не используется — качаем напрямую из Docker Hub
docker run -d \
  --name debug-refactor-go \
  --restart unless-stopped \
  -p 80:5000 \
  -v go_data:/data \
  markmus11012020/debug-refactor:go-1.0.0

# Или через compose
docker compose up -d
```

Проверка состояния:

```bash
docker ps
docker logs -f debug-refactor-go    # Ctrl+C для выхода
docker exec -it debug-refactor-go ls /data   # данные внутри тома
```

### Шаг 6. Открыть порты в файрволe

```bash
# UFW
sudo ufw allow 80/tcp
sudo ufw allow OpenSSH
sudo ufw enable

# iptables (если UFW нет)
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
```

Если сервер за cloud-фаерволом (AWS Security Group, GCP Firewall и т.п.) —
добавьте inbound-правило TCP/80 для вашего IP/подсети.

### Шаг 7. HTTPS (рекомендуется)

```bash
# Самый быстрый способ — Caddy (автоматический Let's Encrypt):
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# /etc/caddy/Caddyfile
:80 {
    reverse_proxy debug-refactor-go:5000
}
sudo systemctl reload caddy
```

### Шаг 8. Проверка эндпоинтов на сервере

```bash
# Изнутри сервера
curl http://127.0.0.1/health
./scripts/test_endpoints.sh

# С вашей машины (пример)
BASE_URL=http://my-server ./scripts/test_endpoints.sh
```

### Шаг 9. Обновление версии

```bash
cd ~/debug-refactor
docker compose pull                # если compose
# или
docker pull markmus11012020/debug-refactor:go-1.0.1
docker stop debug-refactor-go
docker rm   debug-refactor-go
docker run -d --name debug-refactor-go --restart unless-stopped \
  -p 80:5000 -v go_data:/data markmus11012020/debug-refactor:go-1.0.1
```

### Шаг 10. Бэкап данных

```bash
docker run --rm -v go_data:/data -v $(pwd):/backup \
  busybox tar czf /backup/users-$(date +%F).tar.gz /data
```

---

## 📋 Чек-лист «запустить на новом сервере за 5 минут»

1. `ssh user@server`
2. Установить Docker (`get-docker.sh`).
3. Скопировать `docker-compose.yml` + `scripts/`.
4. `docker compose up -d`.
5. Открыть порт 80 в firewall.
6. `curl http://127.0.0.1/health` → `{"status":"ok"}`.
7. `./scripts/test_endpoints.sh` → `All 13 checks passed.`