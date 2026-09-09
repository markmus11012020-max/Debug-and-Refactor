#!/usr/bin/env bash
# ==========================================================
# scripts/test_endpoints.sh
# Проверяет каждый эндпоинт API (Flask/Go) на ошибки
# и печатает понятный отчёт.
#
# Использование:
#   ./scripts/test_endpoints.sh                     # http://127.0.0.1:5000
#   BASE_URL=http://server:5000 ./scripts/test_endpoints.sh
#   CONTAINER=debug-refactor-go ./scripts/test_endpoints.sh
# ==========================================================
set -u

BASE_URL="${BASE_URL:-http://127.0.0.1:5000}"
CONTAINER="${CONTAINER:-}"

PASS=0
FAIL=0

# ---------- утилиты ----------
color() { printf "\033[%sm%s\033[0m" "$1" "$2"; }
ok()    { color "1;32" "✓"; }
bad()   { color "1;31" "✗"; }
info()  { color "1;36" "›"; }

hr() { printf '%s\n' "------------------------------------------------------------"; }

step() {
  local name="$1" expect="$2" method="$3" path="$4" body="${5:-}"
  local code body_file
  body_file=$(mktemp)

  if [[ -n "$body" ]]; then
    code=$(curl -sS -o "$body_file" -w "%{http_code}" \
              -X "$method" "$BASE_URL$path" \
              -H "Content-Type: application/json" \
              -d "$body" || echo "000")
  else
    code=$(curl -sS -o "$body_file" -w "%{http_code}" \
              -X "$method" "$BASE_URL$path" || echo "000")
  fi

  if [[ "$code" == "$expect" ]]; then
    printf "%s %-45s [%s] expected=%s got=%s\n" "$(ok)" "$name" "$method $path" "$expect" "$code"
    PASS=$((PASS+1))
  else
    printf "%s %-45s [%s] expected=%s got=%s\n" "$(bad)" "$name" "$method $path" "$expect" "$code"
    FAIL=$((FAIL+1))
  fi
  printf "    body: "; head -c 300 "$body_file"; printf "\n"
  rm -f "$body_file"
}

# ---------- преамбула ----------
hr
printf "BASE_URL = %s\n" "$BASE_URL"
if [[ -n "$CONTAINER" ]]; then
  printf "Container: %s\n" "$CONTAINER"
  printf "  status: "; docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "(not found)"
fi
hr

# ---------- 1. health ----------
step "healthcheck"           200 GET  "/health"

# ---------- 2. POST /users (создание) ----------
step "create user #1 (alice)" 201 POST "/users" '{"name":"alice","tags":["vip","beta"]}'
step "create user #2 (bob)"   201 POST "/users" '{"name":"bob","tags":[]}'
step "create user — duplicate" 409 POST "/users" '{"name":"alice"}'   # 409 (Go) / 500 (Flask)
step "create user — empty name" 422 POST "/users" '{"name":""}'

# ---------- 3. GET /users/<id> ----------
step "get user #1"            200 GET  "/users/1"
step "get user — not found"   404 GET  "/users/9999"
step "get user — invalid id"  404 GET  "/users/abc"

# ---------- 4. GET /users (список) ----------
step "list users"             200 GET  "/users"

# ---------- 5. POST /users/<id>/password ----------
step "set password #1"        201 POST "/users/1/password" '{"password":"hunter2"}'
step "set password — empty"   422 POST "/users/1/password" '{"password":""}'
step "set password — no user" 404 POST "/users/9999/password" '{"password":"x"}'

# ---------- 6. GET /active ----------
step "active users"           200 GET  "/active"

# ---------- итог ----------
hr
if [[ $FAIL -eq 0 ]]; then
  printf "%s All %d checks passed.\n" "$(ok)" "$PASS"
  exit 0
else
  printf "%s %d/%d checks FAILED.\n" "$(bad)" "$FAIL" "$((PASS+FAIL))"
  exit 1
fi