# macOS quick tunnel runbook (Team A -> Team B)

This guide is for technically strong developers who are new to macOS process/runtime details.

Goal:
- Team A runs chatbot services on a macOS laptop.
- Team A exposes temporary public URLs using free Cloudflare Quick Tunnels (`trycloudflare.com`).
- Team B uses only a browser.

## What this setup starts

Four background processes:
- FastAPI server on `127.0.0.1:8800`
- Static web server on `127.0.0.1:8081`
- Cloudflare quick tunnel for API
- Cloudflare quick tunnel for web UI

## Prerequisites (Team A)

- macOS with `bash` or `zsh` (default Terminal is fine).
- Repo cloned locally.
- Python virtual environment exists at `.venv`.
- Dependencies installed from repo root:
  - `pip install -r requirements.txt`
- `cloudflared` installed and available on `PATH`.
  - Easiest install: `brew install cloudflared`.
- `GROQ_API_KEY` exported in the current shell session.

Example to set the key for current shell only:

```bash
export GROQ_API_KEY="gsk_..."
```

## Start script

Note: the checked-in scripts auto-detect repo root when run from `docs/installation/`, so no path edits are required.

Create `docs/installation/start-quick-tunnel.sh` with the following content:

```bash
#!/usr/bin/env bash
# Starts local API + web servers and exposes both via Cloudflare Quick Tunnels.
#
# - API is served locally on 127.0.0.1:8800
# - Web UI is served locally on 127.0.0.1:8081
# - cloudflared creates public trycloudflare.com URLs for each local service
#
# The script writes logs and PID files under .quick-tunnel-runtime so the paired
# stop script can terminate all spawned processes reliably.

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
    # Never treat https://api.trycloudflare.com as the tunnel URL — that is the
    # registration API host in error lines, not the randomized trycloudflare hostname.
    local LogPath="$1"
    local TimeoutSeconds="${2:-90}"

    local Deadline=$(( $(date +%s) + TimeoutSeconds ))
    while [[ $(date +%s) -lt ${Deadline} ]]; do
        if [[ -f "${LogPath}" ]]; then
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

# Start FastAPI locally using the venv interpreter directly.
start_logged_process "API" \
    "\"${VenvPython}\" -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port ${ApiPort}" \
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
    "cd \"${RepoRoot}/web_client\" && \"${VenvPython}\" -m http.server ${WebPort}" \
    "${WebLog}" "${WebPidFile}"

sleep 2  # Allow web server startup before tunnels.

# Start quick tunnel exposing API port.
start_logged_process "API Tunnel" \
    "cloudflared tunnel --url http://127.0.0.1:${ApiPort} --no-autoupdate" \
    "${ApiTunnelLog}" "${ApiTunnelPidFile}"

# Start quick tunnel exposing web port.
start_logged_process "Web Tunnel" \
    "cloudflared tunnel --url http://127.0.0.1:${WebPort} --no-autoupdate" \
    "${WebTunnelLog}" "${WebTunnelPidFile}"

echo ""
echo "Waiting for tunnel URLs..."

# Read generated public URLs from tunnel logs.
ApiPublic="$(wait_for_url_in_log "${ApiTunnelLog}")"
WebPublic="$(wait_for_url_in_log "${WebTunnelLog}")"

echo ""
echo "==== PUBLIC URLS ===="
echo "Web URL: ${WebPublic}"
echo "API URL: ${ApiPublic}"
echo "====================="
echo ""

if [[ -z "${WebPublic}" || -z "${ApiPublic}" ]]; then
    # Tell operator exactly where diagnostics live.
    echo "WARNING: Could not detect one/both URLs yet. Check logs in ${RuntimeDir}" >&2
else
    # Team B only needs web URL; API URL is entered in UI settings.
    echo "Team B should open: ${WebPublic}"
    echo "In web UI settings, set API base URL to: ${ApiPublic}"
fi

echo ""
echo "Logs: ${RuntimeDir}"
echo "To stop all processes, run stop-quick-tunnel.sh"
```

Make it executable once:

```bash
chmod +x docs/installation/start-quick-tunnel.sh
```

## Stop script

Create `docs/installation/stop-quick-tunnel.sh` with the following content:

```bash
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

echo "Done."
```

Make it executable once:

```bash
chmod +x docs/installation/stop-quick-tunnel.sh
```

## How Team A runs it

From a Terminal (bash or zsh), in `docs/installation/`:

```bash
./start-quick-tunnel.sh
```

Or from anywhere in the repo:

```bash
bash docs/installation/start-quick-tunnel.sh
```

To stop:

```bash
./stop-quick-tunnel.sh
```

## What Team B does

- Open the **Web URL** printed by Team A (a `https://...trycloudflare.com` URL).
- In web settings, set API base URL to Team A's printed **API URL**.

## Troubleshooting: both URLs showed `https://api.trycloudflare.com`

That hostname is **Cloudflare’s quick-tunnel registration API**, not your public site. It appears in log lines such as `Post "https://api.trycloudflare.com/tunnel": …`. The start script used to mistake that for the tunnel URL; current `start-quick-tunnel.sh` filters it out and waits for the real **`https://<random>.trycloudflare.com`** hostname.

If the script now prints **no** URL (or `UNAVAILABLE` in `api-public-url.txt`), open `tunnel-api.log` and look for **`failed to request quick Tunnel`**. That usually means the machine or network (VPN, firewall, proxy) could not reach `https://api.trycloudflare.com` within the client timeout—fix connectivity, try another network, or adjust VPN/split tunnel, then rerun.

## Troubleshooting: browser “Your connection is not private” / privacy error

Quick Tunnel sites use **HTTPS with a public certificate** for `*.trycloudflare.com`. If Chrome (or another browser) shows a certificate or privacy warning, the tunnel from Team A is usually **not** the root cause.

**Typical causes on Team B’s machine or network**

1. **Corporate, school, or guest Wi‑Fi with TLS inspection** — A middlebox decrypts HTTPS and re‑encrypts with a **local “fake” certificate**. The browser correctly refuses it unless that network’s root CA is installed (often only on employer‑managed laptops).

2. **Antivirus or “web shield” HTTPS scanning** — Same effect as (1): the AV presents its own cert instead of Cloudflare’s.

3. **Wrong date or time** — Very skewed clocks make any certificate look invalid (`NET::ERR_CERT_DATE_INVALID`).

4. **Captive portal** — The network may intercept traffic until you complete login in another tab.

**What to try**

- Use **another network** that does not inspect HTTPS (e.g. phone hotspot or home Wi‑Fi) to confirm it works there.
- On a **managed** laptop, use VPN or a network path your org allows for browser traffic, or ask IT whether `*.trycloudflare.com` must be allowlisted / exempted from SSL inspection.
- Check **system time** is automatic and correct.
- Try **another browser** with extensions disabled (rules out broken extensions).

**Avoid** training people to click “Advanced → proceed” on every warning: that bypasses protections and may violate policy. Use it only if your organization accepts the risk for a short test, and only on a URL you know came from Team A’s live tunnel.

## Notes and caveats

- Quick tunnel URLs are temporary and may change after restart/disconnect.
- Keep Team A machine awake and online for session continuity.
  - Useful command: `caffeinate -dimsu &` (run while session is active; remember to `kill` it after).
- Do not commit secrets (especially `GROQ_API_KEY`).
- For quick tunnels, API CORS should allow the tunnel origin; the easiest test setting is `CLIMATE_API_CORS_ORIGINS='*'` and the checked-in `start-quick-tunnel.sh` defaults to this if not set.

## Troubleshooting: "failed to fetch"

If Team B can open the web UI but chat requests fail, use this checklist.

1) Confirm both tunnels exist
- You need two public URLs, not one:
  - Web tunnel -> local `127.0.0.1:8081`
  - API tunnel -> local `127.0.0.1:8800`

2) Confirm UI API base URL
- In the web app settings, API base URL must be the API tunnel URL:
  - `https://<api-random>.trycloudflare.com`
- Do not use `http://127.0.0.1:8800` in a remote browser.

3) Confirm API tunnel health endpoint
- From any browser, open:
  - `https://<api-random>.trycloudflare.com/health`
- Expected: JSON health response (not Cloudflare or browser error).

4) Confirm CORS
- For quick-tunnel testing, easiest safe temporary setting is:
  - `CLIMATE_API_CORS_ORIGINS='*'`
- The checked-in `start-quick-tunnel.sh` defaults to `*` if not set.

5) Restart stack after fixes
- Re-run:
  - `./start-quick-tunnel.sh`
- Re-copy the newly printed URLs (they may change per session).

6) If still failing, capture these for debugging
- Web tunnel URL
- API tunnel URL
- Result of `https://<api-random>.trycloudflare.com/health`
- Relevant logs under `.quick-tunnel-runtime/`

## Troubleshooting: tunnel returns 502 Bad Gateway

If the **web** tunnel works but the **API** tunnel returns `502 Bad Gateway`, the FastAPI server died before it could bind `127.0.0.1:8800`. The tunnel is fine — there's nothing on the other end.

Check from Team A's machine:

```bash
curl -i http://127.0.0.1:8800/health
tail -n 40 .quick-tunnel-runtime/api.log
```

Common causes seen in `api.log`:

- `ModuleNotFoundError: No module named 'groq'` (or any other dep) **with a traceback path under `/opt/anaconda3/...`** — Anaconda's Python is being used instead of `.venv`. The fix in this script is to invoke `${RepoRoot}/.venv/bin/python` directly. If you still see this, your `.venv` is missing dependencies; run from repo root:

  ```bash
  .venv/bin/pip install -r requirements.txt
  ```

- `Address already in use` — something else is on port 8800. Find and stop it:

  ```bash
  lsof -nP -iTCP:8800 -sTCP:LISTEN
  ```

After fixing, restart the stack:

```bash
./stop-quick-tunnel.sh
./start-quick-tunnel.sh
```

The current script also pre-checks `127.0.0.1:8800/health` before starting tunnels, so a broken API now fails fast with the tail of `api.log` printed to the terminal, instead of silently producing a 502-ing public URL.

## macOS-specific gotchas

- **Gatekeeper / quarantine**: if `cloudflared` was downloaded as a binary (not via `brew`), macOS may block first launch. Either install with `brew install cloudflared`, or run `xattr -d com.apple.quarantine /path/to/cloudflared` once.
- **Port already in use**: macOS sometimes leaves orphaned listeners. Check with `lsof -nP -iTCP:8800 -sTCP:LISTEN` (or `:8081`) and stop the offending PID.
- **System sleep**: closing the lid or letting the laptop sleep tears down both tunnels. Use `caffeinate -dimsu` while a session is active, or set "Prevent computer from sleeping automatically" in System Settings -> Battery / Lock Screen.
- **Shell differences**: the script uses `bash` explicitly via the shebang. Default macOS Terminal is `zsh`, but invoking `./start-quick-tunnel.sh` runs it under `bash`, which the system provides at `/usr/bin/bash`.
