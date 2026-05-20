#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/.remote-test-runtime"
PID_DIR="${RUNTIME_DIR}/pids"

stop_service() {
  local name="$1"
  local pid_file="${PID_DIR}/${name}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: not running (no pid file)"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"

  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "${pid}" >/dev/null 2>&1; then
      kill -9 "${pid}" >/dev/null 2>&1 || true
    fi
    echo "${name}: stopped (pid ${pid})"
  else
    echo "${name}: stale pid file removed"
  fi

  rm -f "${pid_file}"
}

stop_service "tunnel-web"
stop_service "tunnel-api"
stop_service "web"
stop_service "api"

echo "Remote test stack stopped."
