# syntax=docker/dockerfile:1.6
# ==========================================================
# Dockerfile — мульти-сборка: по умолчанию собирает Go-сервер.
# Для Python-версии:  docker build --target python -t app:py .
# Для Go-версии:      docker build -t app:go .
# ==========================================================

# ---------- 1. Python-сервис (Flask) ----------
FROM python:3.12-slim AS python

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Системные зависимости (curl — для healthcheck в compose)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

COPY api ./api
COPY db_manager ./db_manager
COPY tests ./tests
COPY utils.py wsgi.py ./
COPY .env.example ./.env.example

ENV DB_PATH=/data/users.db \
    PASSWORDS_FILE=/data/passwords.txt \
    BCRYPT_ROUNDS=12 \
    ACTIVE_USERS_MAXLEN=5 \
    API_HOST=0.0.0.0 \
    API_PORT=5000 \
    API_DEBUG=0

EXPOSE 5000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:5000/health || exit 1

CMD ["python", "wsgi.py"]


# ---------- 2. Go-сервис (по умолчанию) ----------
FROM golang:1.22-alpine AS go-builder

WORKDIR /src

# Кэширование модулей
COPY go-server/go.mod ./
RUN go mod download

COPY go-server/ ./
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-s -w" \
    -o /out/go-server \
    ./cmd/server


FROM gcr.io/distroless/static-debian12:nonroot AS go

LABEL org.opencontainers.image.title="go-server" \
      org.opencontainers.image.description="Debug & Refactor — Go port (net/http + sqlite)" \
      org.opencontainers.image.source="https://github.com/markmus11012020-max/Debug-and-Refactor"

COPY --from=go-builder /out/go-server /go-server

ENV DB_PATH=/data/users.db \
    PASSWORDS_FILE=/data/passwords.txt \
    BCRYPT_ROUNDS=12 \
    ACTIVE_USERS_MAXLEN=5 \
    API_HOST=0.0.0.0 \
    API_PORT=5000

EXPOSE 5000
VOLUME ["/data"]

USER nonroot:nonroot

ENTRYPOINT ["/go-server"]