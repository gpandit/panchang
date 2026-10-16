#!/usr/bin/env bash
# The Pandit local development deployment helper.
#
# Usage:
#   ./deploy.sh up       # infrastructure, migrations, API, and PCS
#   ./deploy.sh status   # health and process status
#   ./deploy.sh logs     # follow API and PCS logs
#   ./deploy.sh down     # stop app processes and infrastructure (keeps volumes)
#
# This script is deliberately development-only. It never deploys to a remote
# host, never removes volumes, and refuses non-development build profiles.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/infra/docker-compose.yml}"
STATE_DIR="${DEV_STATE_DIR:-${ROOT_DIR}/.tmp/dev}"

usage() {
  sed -n '2,14p' "$0"
}

die() {
  printf 'deploy.sh: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command is missing: $1"
}

load_environment() {
  if [[ ! -f "$ENV_FILE" ]]; then
    [[ -f "${ROOT_DIR}/.env.example" ]] || die "missing ${ROOT_DIR}/.env.example"
    cp "${ROOT_DIR}/.env.example" "$ENV_FILE"
    printf 'Created %s from .env.example (local development defaults).\n' "$ENV_FILE"
  fi

  # The checked-in development example contains shell-compatible assignments.
  # Export them so Alembic and the two uvicorn processes use the same config as
  # Docker Compose without printing any values or secrets.
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a

  # Root .env uses repository-relative paths; the services may be launched
  # from any working directory by uv, so make the ephemeris path unambiguous.
  if [[ "${PANCHANG_EPHEMERIS_PATH:-}" != /* ]]; then
    PANCHANG_EPHEMERIS_PATH="${ROOT_DIR}/${PANCHANG_EPHEMERIS_PATH:-libs/ephemeris}"
    export PANCHANG_EPHEMERIS_PATH
  fi

  [[ "${API_ENVIRONMENT:-development}" == "development" ]] \
    || die "API_ENVIRONMENT must be development"
  [[ "${PANCHANG_BUILD_PROFILE:-development}" == "development" ]] \
    || die "PANCHANG_BUILD_PROFILE must be development"
  [[ -d "${ROOT_DIR}/libs/ephemeris" ]] \
    || die "libs/ephemeris is missing"
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

wait_for() {
  local description="$1"
  shift
  local attempts=60
  local attempt
  for attempt in $(seq 1 "$attempts"); do
    if "$@" >/dev/null 2>&1; then
      printf '%s: ready\n' "$description"
      return 0
    fi
    sleep 2
  done
  printf '%s: not ready after %s seconds\n' "$description" "$((attempts * 2))" >&2
  return 1
}

wait_for_url() {
  local description="$1"
  local url="$2"
  wait_for "$description" curl -fsS --max-time 3 "$url"
}

infra_up() {
  printf 'Starting PostgreSQL/PostGIS, Redis, and MinIO...\n'
  compose up -d postgres redis minio
  wait_for "PostgreSQL/PostGIS" compose exec -T postgres pg_isready \
    -U "${POSTGRES_USER:-pandit}" -d "${POSTGRES_DB:-pandit_dev}"
  wait_for "Redis" compose exec -T redis redis-cli ping
  wait_for_url "MinIO" "http://127.0.0.1:${MINIO_API_PORT:-9000}/minio/health/live"
}

migrate() {
  printf 'Applying API database migrations...\n'
  (
    cd "$ROOT_DIR/services/api"
    uv run alembic upgrade head
  )
}

pid_file() {
  printf '%s/%s.pid' "$STATE_DIR" "$1"
}

log_file() {
  printf '%s/%s.log' "$STATE_DIR" "$1"
}

process_is_running() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "$name")"
  [[ -f "$pid_path" ]] || return 1
  local pid
  pid="$(<"$pid_path")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

start_process() {
  local name="$1"
  shift
  mkdir -p "$STATE_DIR"
  if process_is_running "$name"; then
    printf '%s is already running (pid %s)\n' "$name" "$(<"$(pid_file "$name")")"
    return 0
  fi

  rm -f "$(pid_file "$name")"
  printf 'Starting %s...\n' "$name"
  nohup "$@" >"$(log_file "$name")" 2>&1 < /dev/null &
  printf '%s\n' "$!" >"$(pid_file "$name")"
}

stop_process() {
  local name="$1"
  local pid_path
  pid_path="$(pid_file "$name")"
  [[ -f "$pid_path" ]] || return 0
  local pid
  pid="$(<"$pid_path")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    printf 'Stopping %s (pid %s)...\n' "$name" "$pid"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_path"
}

app_up() {
  mkdir -p "$STATE_DIR"
  start_process panchang uv run --project "$ROOT_DIR/services/panchang" uvicorn \
    panchang.app:app --host "${PANCHANG_HOST:-0.0.0.0}" --port "${PANCHANG_PORT:-8001}"
  start_process api uv run --project "$ROOT_DIR/services/api" uvicorn \
    api.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"

  if [[ "${START_WORKER:-0}" == "1" ]]; then
    start_process worker uv run --project "$ROOT_DIR/services/api" python -m api.worker
  fi

  wait_for_url "Panchang service" "http://127.0.0.1:${PANCHANG_PORT:-8001}/health"
  wait_for_url "API gateway" "http://127.0.0.1:${API_PORT:-8000}/healthz"
}

status() {
  printf 'Development services:\n'
  compose ps
  for name in panchang api worker; do
    if process_is_running "$name"; then
      printf '  %-10s running (pid %s)\n' "$name" "$(<"$(pid_file "$name")")"
    else
      printf '  %-10s stopped\n' "$name"
    fi
  done
  wait_for_url "Panchang service" "http://127.0.0.1:${PANCHANG_PORT:-8001}/health"
  wait_for_url "API gateway" "http://127.0.0.1:${API_PORT:-8000}/healthz"
}

down() {
  stop_process worker
  stop_process api
  stop_process panchang
  compose down
  printf 'Development services stopped. Docker volumes were preserved.\n'
}

logs() {
  mkdir -p "$STATE_DIR"
  touch "$(log_file panchang)" "$(log_file api)"
  tail -f "$(log_file panchang)" "$(log_file api)"
}

main() {
  local action="${1:-up}"
  case "$action" in
    -h|--help|help)
      usage
      ;;
    up|deploy)
      require_command docker
      require_command curl
      require_command uv
      load_environment
      infra_up
      migrate
      app_up
      printf '\nDevelopment deployment is ready:\n'
      printf '  API:      http://localhost:%s\n' "${API_PORT:-8000}"
      printf '  API docs: http://localhost:%s/docs\n' "${API_PORT:-8000}"
      printf '  PCS:      http://localhost:%s\n' "${PANCHANG_PORT:-8001}"
      printf '  MinIO:    http://localhost:%s\n' "${MINIO_CONSOLE_PORT:-9001}"
      ;;
    status)
      require_command docker
      require_command curl
      load_environment
      status
      ;;
    down)
      require_command docker
      load_environment
      down
      ;;
    logs)
      load_environment
      logs
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
