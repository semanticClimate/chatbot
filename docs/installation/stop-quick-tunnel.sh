#!/usr/bin/env bash
# Stops all processes started by start-quick-tunnel.sh.
#
# Reads PID files from .quick-tunnel-runtime and stops each process if alive.
# Removes PID files afterward so next startup begins cleanly.

set -euo pipefail

# Resolve script directory, robust to symlinks.
ScriptDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect repo root whether script is placed at repo root or docs/installation.
if [[ -f "${ScriptDir}/requirements.txt" ]]; then
    RepoRoot="${ScriptDir}"
elif [[ -f "${ScriptDir}/../../requirements.txt" ]]; then
    RepoRoot="$(cd "${ScriptDir}/../.." && pwd)"
else
    echo "Could not locate repo root (requirements.txt not found)." >&2
    exit 1
fi

# Runtime folder shared with start script.
RuntimeDir="${RepoRoot}/.quick-tunnel-runtime"

# Keep in sync with start-quick-tunnel.sh (local bind ports).
ApiPort=8800
WebPort=8081

# PID files tracked for API, web, and both tunnels.
PidFiles=("api.pid" "web.pid" "tunnel-api.pid" "tunnel-web.pid")

for f in "${PidFiles[@]}"; do
    PidPath="${RuntimeDir}/${f}"
    if [[ -f "${PidPath}" ]]; then
        # Read recorded process ID.
        Pid="$(cat "${PidPath}" || true)"
        if [[ -n "${Pid}" ]]; then
            if kill -0 "${Pid}" >/dev/null 2>&1; then
                # Try graceful stop, then escalate to SIGKILL if needed.
                kill "${Pid}" >/dev/null 2>&1 || true
                sleep 1
                if kill -0 "${Pid}" >/dev/null 2>&1; then
                    kill -9 "${Pid}" >/dev/null 2>&1 || true
                fi
                echo "Stopped PID ${Pid}"
            else
                # Process may already be gone; keep cleanup idempotent.
                echo "PID ${Pid} not running."
            fi
        fi
        # Remove PID file even if process was already stopped.
        rm -f "${PidPath}"
    fi
done

# Orphan listeners: PID files referenced bash while Python/cloudflared was the real
# server, or manual kills left children behind — clear our dev ports unconditionally.
cleanup_port_listen() {
    local port="$1"
    if ! command -v lsof >/dev/null 2>&1; then
        return 0
    fi
    local pids
    pids="$(lsof -nP -iTCP:${port} -sTCP:LISTEN -t 2>/dev/null || true)"
    [[ -z "${pids// }" ]] && return 0
    for pid in ${pids}; do
        if kill -0 "${pid}" >/dev/null 2>&1; then
            kill "${pid}" >/dev/null 2>&1 || true
        fi
    done
    sleep 1
    pids="$(lsof -nP -iTCP:${port} -sTCP:LISTEN -t 2>/dev/null || true)"
    for pid in ${pids}; do
        if kill -0 "${pid}" >/dev/null 2>&1; then
            kill -9 "${pid}" >/dev/null 2>&1 || true
            echo "Force-stopped straggler PID ${pid} on port ${port}"
        fi
    done
}

cleanup_port_listen "${ApiPort}"
cleanup_port_listen "${WebPort}"

# Remove tunnel hint so plain local http.server doesn't serve a stale API URL.
rm -f "${RepoRoot}/frontend/tunnel-api-base.txt"

echo "Done."
