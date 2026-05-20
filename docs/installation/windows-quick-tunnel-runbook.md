# Windows quick tunnel runbook (Team A -> Team B)

This guide is for technically strong developers who are new to Windows process/runtime details.

Goal:
- Team A runs chatbot services on a Windows laptop.
- Team A exposes temporary public URLs using free Cloudflare Quick Tunnels (`trycloudflare.com`).
- Team B uses only a browser.

## What this setup starts

Four background processes:
- FastAPI server on `127.0.0.1:8800`
- Static web server on `127.0.0.1:8081`
- Cloudflare quick tunnel for API
- Cloudflare quick tunnel for web UI

## Prerequisites (Team A)

- Windows PowerShell available.
- Repo cloned locally.
- Python virtual environment exists at `.venv`.
- Dependencies installed from repo root:
  - `pip install -r requirements.txt`
- `cloudflared` installed and available on `PATH`.
- `GROQ_API_KEY` exported in the current PowerShell session.

Example to set key for current shell only:

```powershell
$env:GROQ_API_KEY = "gsk_..."
```

## Start script

Note: the checked-in scripts auto-detect repo root when run from `docs/installation/`, so no path edits are required.

Create `docs/installation/start-quick-tunnel.ps1` with the following content:

```powershell
<#
.SYNOPSIS
Starts local API + web servers and exposes both via Cloudflare Quick Tunnels.

.DESCRIPTION
This script is designed for temporary, free-tier remote testing:
- API is served locally on 127.0.0.1:8800
- Web UI is served locally on 127.0.0.1:8081
- cloudflared creates public trycloudflare.com URLs for each local service

The script writes logs and PID files under .quick-tunnel-runtime so the paired
stop script can terminate all spawned processes reliably.
#>

$ErrorActionPreference = "Stop"  # Fail fast on all command errors.

# Resolve repository root as the directory containing this script file.
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Expected venv activation script path for Windows PowerShell.
$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

# Local service ports (web is 8081 to avoid common clashes on 8080).
$ApiPort = 8800
$WebPort = 8081

# Runtime directory for logs and PID files.
$RuntimeDir = Join-Path $RepoRoot ".quick-tunnel-runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

# Log file paths (one log per process for easier troubleshooting).
$ApiLog       = Join-Path $RuntimeDir "api.log"
$WebLog       = Join-Path $RuntimeDir "web.log"
$ApiTunnelLog = Join-Path $RuntimeDir "tunnel-api.log"
$WebTunnelLog = Join-Path $RuntimeDir "tunnel-web.log"

# PID files used by the stop script to terminate spawned processes.
$ApiPidFile       = Join-Path $RuntimeDir "api.pid"
$WebPidFile       = Join-Path $RuntimeDir "web.pid"
$ApiTunnelPidFile = Join-Path $RuntimeDir "tunnel-api.pid"
$WebTunnelPidFile = Join-Path $RuntimeDir "tunnel-web.pid"

function Start-LoggedProcess {
    <#
    .SYNOPSIS
    Starts a command in a minimized child PowerShell process and logs output.

    .PARAMETER Title
    Human-friendly label printed to console.

    .PARAMETER Command
    Command string executed from repo root.

    .PARAMETER LogPath
    Output log file path.

    .PARAMETER PidFile
    PID file path written for later shutdown.
    #>
    param(
        [string]$Title,
        [string]$Command,
        [string]$LogPath,
        [string]$PidFile
    )

    # Wrap command so it runs from repo root and captures stdout/stderr to log.
    $wrapped = "cd `"$RepoRoot`"; $Command *> `"$LogPath`""

    # Start detached child PowerShell to keep parent console free.
    $p = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command $wrapped" `
        -WindowStyle Minimized -PassThru

    # Persist child PID for deterministic stop behavior.
    Set-Content -Path $PidFile -Value $p.Id
    Write-Host "$Title started (PID $($p.Id))"
}

function Wait-ForUrlInLog {
    <#
    .SYNOPSIS
    Polls a log file until a trycloudflare.com URL appears or timeout occurs.

    .PARAMETER LogPath
    Tunnel log file to parse.

    .PARAMETER TimeoutSeconds
    Max wait time before returning null.
    #>
    param(
        [string]$LogPath,
        [int]$TimeoutSeconds = 90
    )

    # Compute deadline once and poll in short intervals.
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $LogPath) {
            # Exclude https://api.trycloudflare.com — registrar host in errors, not public URL.
            $urls = Select-String -Path $LogPath -Pattern 'https://[a-zA-Z0-9\.-]+\.trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue |
                ForEach-Object { $_.Matches } |
                ForEach-Object { $_.Value } |
                Where-Object { $_ -ne 'https://api.trycloudflare.com' }
            if ($urls) {
                return @($urls)[-1]
            }
        }
        Start-Sleep -Milliseconds 700  # Small sleep to reduce log polling overhead.
    }
    return $null
}

# Validate venv exists before spawning any child process.
if (-not (Test-Path $VenvActivate)) {
    throw "Missing venv activate script: $VenvActivate"
}

# Validate cloudflared is installed and available in PATH.
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared not found in PATH. Install cloudflared first."
}

# Validate API key exists in current shell environment.
if (-not $env:GROQ_API_KEY) {
    throw "GROQ_API_KEY is not set in this PowerShell session."
}

# Set API CORS to local web origin for browser -> API requests.
$env:CLIMATE_API_CORS_ORIGINS = "http://127.0.0.1:$WebPort"

# Start FastAPI process (local-only bind, externally exposed by tunnel).
Start-LoggedProcess -Title "API" `
    -Command ". `"$VenvActivate`"; python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port $ApiPort" `
    -LogPath $ApiLog -PidFile $ApiPidFile

Start-Sleep -Seconds 2  # Give API a moment to initialize before next steps.

# Start static web server process from web_client directory.
Start-LoggedProcess -Title "Web UI" `
    -Command ". `"$VenvActivate`"; cd `"$RepoRoot\web_client`"; python -m http.server $WebPort" `
    -LogPath $WebLog -PidFile $WebPidFile

Start-Sleep -Seconds 2  # Give web server a moment to bind port 8081.

# Start Cloudflare quick tunnel for API endpoint.
Start-LoggedProcess -Title "API Tunnel" `
    -Command "cloudflared tunnel --url http://127.0.0.1:$ApiPort --no-autoupdate" `
    -LogPath $ApiTunnelLog -PidFile $ApiTunnelPidFile

# Start Cloudflare quick tunnel for web endpoint.
Start-LoggedProcess -Title "Web Tunnel" `
    -Command "cloudflared tunnel --url http://127.0.0.1:$WebPort --no-autoupdate" `
    -LogPath $WebTunnelLog -PidFile $WebTunnelPidFile

Write-Host ""
Write-Host "Waiting for tunnel URLs..."

# Parse tunnel logs to capture externally shareable URLs.
$ApiPublic = Wait-ForUrlInLog -LogPath $ApiTunnelLog
$WebPublic = Wait-ForUrlInLog -LogPath $WebTunnelLog

Write-Host ""
Write-Host "==== PUBLIC URLS ===="
Write-Host "Web URL: $WebPublic"
Write-Host "API URL: $ApiPublic"
Write-Host "====================="
Write-Host ""

if (-not $WebPublic -or -not $ApiPublic) {
    # Explicit warning helps operator know where to inspect failures.
    Write-Warning "Could not detect one/both URLs yet. Check logs in $RuntimeDir"
} else {
    # Team B only needs web URL; API URL is entered in web app settings.
    Write-Host "Team B should open: $WebPublic"
    Write-Host "In web UI settings, set API base URL to: $ApiPublic"
}

Write-Host ""
Write-Host "Logs: $RuntimeDir"
Write-Host "To stop all processes, run stop-quick-tunnel.ps1"
```

## Stop script

Create `docs/installation/stop-quick-tunnel.ps1` with the following content:

```powershell
<#
.SYNOPSIS
Stops all processes started by start-quick-tunnel.ps1.

.DESCRIPTION
Reads PID files from .quick-tunnel-runtime and force-stops each process if alive.
Removes PID files afterward so the next start is clean.
#>

# Resolve repository root from current script location.
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Runtime folder used by the start script.
$RuntimeDir = Join-Path $RepoRoot ".quick-tunnel-runtime"

# PID files tracked for API, web, and two tunnel processes.
$pidFiles = @("api.pid","web.pid","tunnel-api.pid","tunnel-web.pid") |
    ForEach-Object { Join-Path $RuntimeDir $_ }

foreach ($f in $pidFiles) {
    if (Test-Path $f) {
        # Read PID recorded at process startup.
        $pid = Get-Content $f
        if ($pid) {
            try {
                # Force stop is used because child shells may not exit gracefully.
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Host "Stopped PID $pid"
            } catch {
                # Process may already be gone; continue cleanup.
                Write-Host "PID $pid not running."
            }
        }
        # Remove stale PID files regardless of process stop outcome.
        Remove-Item $f -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Done."
```

## How Team A runs it

From PowerShell, in `docs/installation/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-quick-tunnel.ps1
```

To stop:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-quick-tunnel.ps1
```

## What Team B does

- Open the **Web URL** printed by Team A (a `https://...trycloudflare.com` URL).
- In web settings, set API base URL to Team A’s printed **API URL**.

## Troubleshooting: both URLs showed `https://api.trycloudflare.com`

That hostname is **Cloudflare’s quick-tunnel registration API**, not your public site. It appears in log lines such as `Post "https://api.trycloudflare.com/tunnel": …`. The start script used to mistake that for the tunnel URL; current `start-quick-tunnel.ps1` / `start-quick-tunnel.sh` filters it out and waits for **`https://<random>.trycloudflare.com`**.

If the script prints **no** URL, check `tunnel-api.log` for **`failed to request quick Tunnel`** — often VPN/firewall/proxy blocking `https://api.trycloudflare.com`. Fix connectivity and rerun.

While waiting, the start script prints **`[quick-tunnel …]`** every 10 seconds and waits for **both** tunnels in parallel. Defaults: **`QUICK_TUNNEL_URL_TIMEOUT_SECONDS=300`** and **`QUICK_TUNNEL_EARLY_EXIT_SECONDS=90`** (stop early when both logs show registration failure). Tune: `$env:QUICK_TUNNEL_URL_TIMEOUT_SECONDS = 600; $env:QUICK_TUNNEL_EARLY_EXIT_SECONDS = 0` before `start-quick-tunnel.ps1`.

## Notes and caveats

- Quick tunnel URLs are temporary and may change after restart/disconnect.
- Keep Team A machine awake and online for session continuity.
- Do not commit secrets (especially `GROQ_API_KEY`).
- For quick tunnels, API CORS should allow the tunnel origin; easiest test setting is `CLIMATE_API_CORS_ORIGINS='*'`.

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
- The checked-in `start-quick-tunnel.ps1` now defaults to `*` if not set.

5) Restart stack after fixes
- Re-run:
  - `powershell -ExecutionPolicy Bypass -File .\start-quick-tunnel.ps1`
- Re-copy the newly printed URLs (they may change per session).

6) If still failing, capture these for debugging
- Web tunnel URL
- API tunnel URL
- Result of `https://<api-random>.trycloudflare.com/health`
- Relevant logs under `.quick-tunnel-runtime`
