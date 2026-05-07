#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/.remote-test-runtime"
LOG_DIR="${RUNTIME_DIR}/logs"
PID_DIR="${RUNTIME_DIR}/pids"
PUBLIC_CHAT_URL="${CLIMATE_PUBLIC_CHAT_URL:-https://chat.example.com}"

mkdir -p "${LOG_DIR}" "${PID_DIR}"

if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "GROQ_API_KEY is not set. Export it before running this script."
  exit 1
fi

if [[ -z "${CLIMATE_API_CORS_ORIGINS:-}" ]]; then
  echo "CLIMATE_API_CORS_ORIGINS is not set."
  echo "Example: export CLIMATE_API_CORS_ORIGINS='https://chat.example.com'"
  exit 1
fi

if [[ ! -f "${HOME}/.cloudflared/climate-api.yml" ]]; then
  echo "Missing tunnel config: ${HOME}/.cloudflared/climate-api.yml"
  exit 1
fi

if [[ ! -f "${HOME}/.cloudflared/climate-web.yml" ]]; then
  echo "Missing tunnel config: ${HOME}/.cloudflared/climate-web.yml"
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  echo "Missing virtual environment at ${ROOT_DIR}/.venv"
  echo "Create it with: python -m venv .venv"
  exit 1
fi

# shellcheck disable=SC1091
source "${ROOT_DIR}/.venv/bin/activate"

run_service() {
  local name="$1"
  local command="$2"
  local log_file="${LOG_DIR}/${name}.log"
  local pid_file="${PID_DIR}/${name}.pid"

  if [[ -f "${pid_file}" ]]; then
    local old_pid
    old_pid="$(cat "${pid_file}")"
    if kill -0 "${old_pid}" >/dev/null 2>&1; then
      echo "${name} already running (pid ${old_pid})"
      return
    fi
    rm -f "${pid_file}"
  fi

  nohup bash -lc "${command}" >"${log_file}" 2>&1 &
  local new_pid=$!
  echo "${new_pid}" >"${pid_file}"
  echo "Started ${name} (pid ${new_pid})"
}

run_service "api" "cd '${ROOT_DIR}' && python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800"
run_service "web" "cd '${ROOT_DIR}/web_client' && python -m http.server 8080"
run_service "tunnel-api" "cloudflared tunnel --config '${HOME}/.cloudflared/climate-api.yml' run"
run_service "tunnel-web" "cloudflared tunnel --config '${HOME}/.cloudflared/climate-web.yml' run"

echo
echo "Remote test stack started."
echo "Share this URL with testers: ${PUBLIC_CHAT_URL}"
echo "Logs: ${LOG_DIR}"
echo "Stop all services with: bash scripts/stop_remote_test.sh"
