#!/usr/bin/env bash
# Starts local API + web servers and exposes both via Cloudflare Quick Tunnels.
#
# - API is served locally on 127.0.0.1:8800
# - Web UI is served locally on 127.0.0.1:8081
# - cloudflared creates public trycloudflare.com URLs for each local service
#
# The script writes logs and PID files under .quick-tunnel-runtime so the paired
# stop script can terminate all spawned processes reliably.
#
# Run with:  bash path/to/start-quick-tunnel.sh
# Do not:   source path/to/start-quick-tunnel.sh  (breaks job control and $0)

set -euo pipefail

# Resolve script directory, robust to symlinks.
ScriptDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sourcing would run in the interactive shell (messy jobs, wrong $0) and must be refused.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    printf '%s\n' "Do not source this script. Run: bash \"${ScriptDir}/$(basename "${BASH_SOURCE[0]}")\"" >&2
    return 1 2>/dev/null || exit 1
fi

# Auto-detect repo root whether script is placed at repo root or docs/installation.
if [[ -f "${ScriptDir}/requirements.txt" ]]; then
    RepoRoot="${ScriptDir}"
elif [[ -f "${ScriptDir}/../../requirements.txt" ]]; then
    RepoRoot="$(cd "${ScriptDir}/../.." && pwd)"
else
    echo "Could not locate repo root (requirements.txt not found)." >&2
    exit 1
fi

# Use absolute path to the venv interpreter so we are immune to PATH games
# (e.g. conda / anaconda init in the user's shell profile that can otherwise
# shadow `.venv/bin/python` when child shells re-source the profile).
VenvPython="${RepoRoot}/.venv/bin/python"

# Local service ports (web uses 8081 to avoid common 8080 conflicts).
ApiPort=8800
WebPort=8081

# Shared runtime folder for logs and PID files.
RuntimeDir="${RepoRoot}/.quick-tunnel-runtime"
mkdir -p "${RuntimeDir}"

# End any still-running processes from a previous run (same PID files / ports).
# stop-quick-tunnel.sh is idempotent: if nothing is running or no PID files exist, it no-ops.
StopScript="${ScriptDir}/stop-quick-tunnel.sh"
if [[ -f "${StopScript}" ]]; then
    echo "Stopping any prior quick-tunnel processes..."
    bash "${StopScript}" || true
    sleep 1
fi

# Avoid leaving stale copy-paste URL files from a prior run.
rm -f "${RuntimeDir}/api-public-url.txt" "${RuntimeDir}/web-public-url.txt"
rm -f "${RepoRoot}/web_client/tunnel-api-base.txt"

# Per-process log files for easier troubleshooting.
ApiLog="${RuntimeDir}/api.log"
WebLog="${RuntimeDir}/web.log"
ApiTunnelLog="${RuntimeDir}/tunnel-api.log"
WebTunnelLog="${RuntimeDir}/tunnel-web.log"

# PID files used by the stop script.
ApiPidFile="${RuntimeDir}/api.pid"
WebPidFile="${RuntimeDir}/web.pid"
ApiTunnelPidFile="${RuntimeDir}/tunnel-api.pid"
WebTunnelPidFile="${RuntimeDir}/tunnel-web.pid"

start_logged_process() {
    # Start a background command, redirect output to a log, record PID.
    #   $1 Title       Human-friendly process label
    #   $2 Command     Command string executed via `bash -lc` from repo root
    #   $3 LogPath     Path to capture stdout/stderr output
    #   $4 PidFile     Path where spawned PID is written
    local Title="$1"
    local Command="$2"
    local LogPath="$3"
    local PidFile="$4"

    # Run from repo root and redirect all output to process-specific log.
    # Use `bash -c` (not `-lc`) to avoid sourcing the user's login profile,
    # which can re-inject conda/anaconda PATH and shadow the venv.
    nohup bash -c "cd \"${RepoRoot}\" && ${Command}" >"${LogPath}" 2>&1 &
    local NewPid=$!

    # Persist PID for reliable shutdown.
    echo "${NewPid}" >"${PidFile}"
    echo "${Title} started (PID ${NewPid})"
}

wait_for_url_in_log() {
    # Poll a cloudflared log until a *public* Quick Tunnel hostname appears.
    #   $1 LogPath          Log file to scan
    #   $2 TimeoutSeconds   Max wait duration (default 90)
    #
    # cloudflared logs the registration endpoint https://api.trycloudflare.com
    # (e.g. in "Post \"https://api.trycloudflare.com/tunnel\": ... timeout").
    # That string must NOT be treated as the tunnel URL — grep it out.
    local LogPath="$1"
    local TimeoutSeconds="${2:-90}"

    local Deadline=$(( $(date +%s) + TimeoutSeconds ))
    while [[ $(date +%s) -lt ${Deadline} ]]; do
        if [[ -f "${LogPath}" ]]; then
            # -a: cloudflared logs can contain NUL/high bytes; grep else prints
            # "Binary file … matches" to stdout, which we must not capture as the URL.
            local Url
            Url="$(
                LC_ALL=C grep -aEo 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "${LogPath}" 2>/dev/null \
                    | grep -Fxv 'https://api.trycloudflare.com' \
                    | tail -n 1 || true
            )"
            if [[ -n "${Url}" ]]; then
                echo "${Url}"
                return 0
            fi
        fi
        sleep 0.7
    done
    return 1
}

# Fail fast if something still holds the port (avoids uvicorn "address already in use"
# while an older API keeps serving — confusing logs and wrong code version).
abort_if_port_in_use() {
    local port="$1"
    local label="$2"
    if ! command -v lsof >/dev/null 2>&1; then
        return 0
    fi
    if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "ERROR: Port ${port} (${label}) is already in use." >&2
        echo "Usually a previous uvicorn or http.server that was not stopped." >&2
        lsof -nP -iTCP:"${port}" -sTCP:LISTEN >&2
        echo "Run: bash \"${ScriptDir}/stop-quick-tunnel.sh\"  then wait a few seconds and try again." >&2
        exit 1
    fi
}

# Ensure venv interpreter exists before launching dependent processes.
if [[ ! -x "${VenvPython}" ]]; then
    echo "Missing venv interpreter: ${VenvPython}" >&2
    echo "Create the venv and install deps from repo root:" >&2
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# Ensure cloudflared is installed and on PATH.
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared not found in PATH. Install it (e.g. brew install cloudflared)." >&2
    exit 1
fi

# Ensure API key exists in current shell environment.
if [[ -z "${GROQ_API_KEY:-}" ]]; then
    echo "GROQ_API_KEY is not set in this shell session." >&2
    exit 1
fi

# For quick-tunnel testing, default to permissive CORS unless already provided.
if [[ -z "${CLIMATE_API_CORS_ORIGINS:-}" ]]; then
    export CLIMATE_API_CORS_ORIGINS="*"
fi

# Forward env vars that child shells need (GROQ_API_KEY, CORS).
export GROQ_API_KEY
export CLIMATE_API_CORS_ORIGINS

abort_if_port_in_use "${ApiPort}" "API (uvicorn)"
abort_if_port_in_use "${WebPort}" "Web UI (http.server)"

# Start FastAPI locally using the venv interpreter directly.
# Use exec so PID file is uvicorn itself (bash would otherwise orphan the child).
start_logged_process "API" \
    "exec \"${VenvPython}\" -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port ${ApiPort}" \
    "${ApiLog}" "${ApiPidFile}"

# Wait for the API to actually accept connections before starting tunnels.
# If we skip this and the API crashes on import, cloudflared still happily
# publishes a public URL that returns 502 Bad Gateway, which looks like a
# tunnel/CORS bug to remote testers.
echo "Waiting for API to come up on 127.0.0.1:${ApiPort}..."
ApiReady=0
for _ in $(seq 1 30); do
    if curl -fsS -o /dev/null "http://127.0.0.1:${ApiPort}/health"; then
        ApiReady=1
        break
    fi
    sleep 1
done
if [[ "${ApiReady}" -ne 1 ]]; then
    echo "" >&2
    echo "ERROR: API failed to start on 127.0.0.1:${ApiPort}." >&2
    echo "Last 20 lines of ${ApiLog}:" >&2
    echo "----------------------------------------" >&2
    tail -n 20 "${ApiLog}" >&2 || true
    echo "----------------------------------------" >&2
    echo "Aborting before starting tunnels. Run stop-quick-tunnel.sh to clean up." >&2
    exit 1
fi
echo "API healthy."

# Start static web server locally using the venv interpreter directly.
start_logged_process "Web UI" \
    "cd \"${RepoRoot}/web_client\" && exec \"${VenvPython}\" -m http.server ${WebPort}" \
    "${WebLog}" "${WebPidFile}"

sleep 2  # Allow web server startup before tunnels.

# Start quick tunnel exposing API port.
start_logged_process "API Tunnel" \
    "exec cloudflared tunnel --url http://127.0.0.1:${ApiPort} --no-autoupdate" \
    "${ApiTunnelLog}" "${ApiTunnelPidFile}"

# Start quick tunnel exposing web port.
start_logged_process "Web Tunnel" \
    "exec cloudflared tunnel --url http://127.0.0.1:${WebPort} --no-autoupdate" \
    "${WebTunnelLog}" "${WebTunnelPidFile}"

echo ""
echo "Waiting for tunnel URLs..."

# Read generated public URLs from tunnel logs.
ApiPublic="$(wait_for_url_in_log "${ApiTunnelLog}" || true)"
WebPublic="$(wait_for_url_in_log "${WebTunnelLog}" || true)"

echo ""
echo "==== PUBLIC URLS ===="
echo "Web URL: ${WebPublic}"
echo "API URL: ${ApiPublic}"
echo "====================="
echo ""

# Copy-paste targets — always created so .quick-tunnel-runtime/ always lists them.
# When cloudflared never prints a URL in time, these contain a clear placeholder (not a valid API URL).
# Hint file served by the static web root so remote browsers default to the API tunnel URL
# (127.0.0.1 would point at the viewer's machine, not Team A's API).
WebTunnelHint="${RepoRoot}/web_client/tunnel-api-base.txt"

if [[ -n "${ApiPublic}" ]]; then
    printf '%s\n' "${ApiPublic}" >"${RuntimeDir}/api-public-url.txt"
    printf '%s\n' "${ApiPublic}" >"${WebTunnelHint}"
else
    printf '%s\n' "UNAVAILABLE — no public https://…trycloudflare.com hostname in tunnel-api.log within 90s (api.trycloudflare.com is the registrar, not your tunnel). See tunnel-api.log." >"${RuntimeDir}/api-public-url.txt"
    rm -f "${WebTunnelHint}"
fi
if [[ -n "${WebPublic}" ]]; then
    printf '%s\n' "${WebPublic}" >"${RuntimeDir}/web-public-url.txt"
else
    printf '%s\n' "UNAVAILABLE — no public https://…trycloudflare.com hostname in tunnel-web.log within 90s. See tunnel-web.log." >"${RuntimeDir}/web-public-url.txt"
fi

if [[ -z "${WebPublic}" || -z "${ApiPublic}" ]]; then
    # Tell operator exactly where diagnostics live.
    echo "WARNING: Could not detect one/both Quick Tunnel URLs. Check logs in ${RuntimeDir}" >&2
    if [[ -f "${ApiTunnelLog}" ]] && LC_ALL=C grep -aFq 'failed to request quick Tunnel' "${ApiTunnelLog}" 2>/dev/null; then
        echo "tunnel-api.log reports quick-tunnel registration failure (often network/VPN/firewall blocking https://api.trycloudflare.com). Fix connectivity, then rerun." >&2
    fi
    echo "The API base URL in the chat UI must be the printed https://…trycloudflare.com URL for the API tunnel, not a .log file path." >&2
    echo "Placeholder lines were written to api-public-url.txt / web-public-url.txt (do not paste those into the UI)." >&2
else
    # Team B only needs web URL; API URL is prefilled from tunnel-api-base.txt when tunnels succeed.
    echo "Team B should open: ${WebPublic}"
    echo "API base URL defaults to: ${ApiPublic} (served as web_client/tunnel-api-base.txt)"
    echo "(Also saved under ${RuntimeDir}/api-public-url.txt for copying.)"
fi

echo ""
echo "Logs: ${RuntimeDir}"
echo "To stop all processes, run stop-quick-tunnel.sh"
