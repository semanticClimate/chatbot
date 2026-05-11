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

$ErrorActionPreference = "Stop"  # Fail fast on command errors.

# Resolve script directory first.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Auto-detect repo root whether script is placed at repo root or docs/installation.
if (Test-Path (Join-Path $ScriptDir "requirements.txt")) {
    $RepoRoot = $ScriptDir
} elseif (Test-Path (Join-Path $ScriptDir "..\..\requirements.txt")) {
    $RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
} else {
    throw "Could not locate repo root (requirements.txt not found)."
}

# Expected Windows venv activation script path.
$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"

# Local service ports (web uses 8081 to avoid common 8080 conflicts).
$ApiPort = 8800
$WebPort = 8081

# Shared runtime folder for logs and PID files.
$RuntimeDir = Join-Path $RepoRoot ".quick-tunnel-runtime"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

# Per-process log files for easier troubleshooting.
$ApiLog       = Join-Path $RuntimeDir "api.log"
$WebLog       = Join-Path $RuntimeDir "web.log"
$ApiTunnelLog = Join-Path $RuntimeDir "tunnel-api.log"
$WebTunnelLog = Join-Path $RuntimeDir "tunnel-web.log"

# PID files used by the stop script.
$ApiPidFile       = Join-Path $RuntimeDir "api.pid"
$WebPidFile       = Join-Path $RuntimeDir "web.pid"
$ApiTunnelPidFile = Join-Path $RuntimeDir "tunnel-api.pid"
$WebTunnelPidFile = Join-Path $RuntimeDir "tunnel-web.pid"

function Start-LoggedProcess {
    <#
    .SYNOPSIS
    Starts a child PowerShell process and redirects output to a log file.

    .PARAMETER Title
    Human-friendly process label.

    .PARAMETER Command
    Command string to execute.

    .PARAMETER LogPath
    Path to capture stdout/stderr output.

    .PARAMETER PidFile
    Path where spawned PID is written.
    #>
    param(
        [string]$Title,
        [string]$Command,
        [string]$LogPath,
        [string]$PidFile
    )

    # Run from repo root and redirect all output to process-specific log.
    $wrapped = "cd `"$RepoRoot`"; $Command *> `"$LogPath`""

    # Start detached process so this control script can continue.
    $p = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command $wrapped" `
        -WindowStyle Minimized -PassThru

    # Persist PID for reliable shutdown.
    Set-Content -Path $PidFile -Value $p.Id
    Write-Host "$Title started (PID $($p.Id))"
}

function Get-QuickTunnelPublicUrlFromLog {
    <#
    .SYNOPSIS
    Returns the newest public quick-tunnel hostname from a cloudflared log, or $null.
    #>
    param([string]$LogPath)
    if (-not (Test-Path $LogPath)) { return $null }
    $urls = Select-String -Path $LogPath -Pattern 'https://[a-zA-Z0-9\.-]+\.trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Matches } |
        ForEach-Object { $_.Value } |
        Where-Object { $_ -ne 'https://api.trycloudflare.com' }
    if (-not $urls) { return $null }
    return @($urls)[-1]
}

function Wait-ForBothQuickTunnelUrls {
    <#
    .SYNOPSIS
    Polls both tunnel logs in parallel with stderr progress every 10s.
    #>
    param(
        [string]$ApiTunnelLog,
        [string]$WebTunnelLog,
        [int]$TimeoutSeconds = 180
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $start = Get-Date
    $lastProgress = $start
    $apiPublic = $null
    $webPublic = $null
    $warned = $false

    while ((Get-Date) -lt $deadline) {
        if (-not $apiPublic) { $apiPublic = Get-QuickTunnelPublicUrlFromLog $ApiTunnelLog }
        if (-not $webPublic) { $webPublic = Get-QuickTunnelPublicUrlFromLog $WebTunnelLog }
        if ($apiPublic -and $webPublic) {
            return @{ Api = $apiPublic; Web = $webPublic }
        }

        $now = Get-Date
        if (($now - $lastProgress).TotalSeconds -ge 10) {
            $lastProgress = $now
            $elapsed = [int](($now - $start).TotalSeconds)
            $aStatus = $(if ($apiPublic) { "ready" } else { "waiting…" })
            $wStatus = $(if ($webPublic) { "ready" } else { "waiting…" })
            Write-Host "[quick-tunnel ${elapsed}s / ${TimeoutSeconds}s max] API tunnel: ${aStatus} · Web tunnel: ${wStatus}" -ForegroundColor DarkGray
            try {
                if (-not $warned -and (Select-String -Path $ApiTunnelLog -Pattern 'failed to request quick Tunnel' -Quiet -ErrorAction SilentlyContinue)) {
                    Write-Host "Hint: tunnel-api.log shows registration errors — try another network or set `$env:QUICK_TUNNEL_URL_TIMEOUT_SECONDS higher." -ForegroundColor DarkYellow
                    $warned = $true
                }
            } catch { }
        }
        Start-Sleep -Milliseconds 700
    }

    return @{ Api = $apiPublic; Web = $webPublic }
}

# Ensure virtual environment exists before launching dependent processes.
if (-not (Test-Path $VenvActivate)) {
    throw "Missing venv activate script: $VenvActivate"
}

# Ensure cloudflared is installed and on PATH.
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared not found in PATH. Install cloudflared first."
}

# Ensure API key exists in current shell environment.
if (-not $env:GROQ_API_KEY) {
    throw "GROQ_API_KEY is not set in this PowerShell session."
}

# For quick-tunnel testing, default to permissive CORS unless already provided.
if (-not $env:CLIMATE_API_CORS_ORIGINS) {
    $env:CLIMATE_API_CORS_ORIGINS = "*"
}

# Start FastAPI locally.
Start-LoggedProcess -Title "API" `
    -Command ". `"$VenvActivate`"; python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port $ApiPort" `
    -LogPath $ApiLog -PidFile $ApiPidFile

Start-Sleep -Seconds 2  # Allow API startup before starting web.

# Start static web server locally.
Start-LoggedProcess -Title "Web UI" `
    -Command ". `"$VenvActivate`"; cd `"$RepoRoot\web_client`"; python -m http.server $WebPort" `
    -LogPath $WebLog -PidFile $WebPidFile

Start-Sleep -Seconds 2  # Allow web server startup before tunnels.

# Start quick tunnel exposing API port.
Start-LoggedProcess -Title "API Tunnel" `
    -Command "cloudflared tunnel --url http://127.0.0.1:$ApiPort --no-autoupdate" `
    -LogPath $ApiTunnelLog -PidFile $ApiTunnelPidFile

# Start quick tunnel exposing web port.
Start-LoggedProcess -Title "Web Tunnel" `
    -Command "cloudflared tunnel --url http://127.0.0.1:$WebPort --no-autoupdate" `
    -LogPath $WebTunnelLog -PidFile $WebTunnelPidFile

$tunnelDeadline = 180
try {
    if ($env:QUICK_TUNNEL_URL_TIMEOUT_SECONDS -match '^\d+$') {
        $tunnelDeadline = [int]$env:QUICK_TUNNEL_URL_TIMEOUT_SECONDS
    }
} catch { }

Write-Host ""
Write-Host "Waiting for tunnel URLs from cloudflared (can take 1–3+ minutes on slow networks)…"
Write-Host "Progress updates every 10s. Increase wait before running again: `$env:QUICK_TUNNEL_URL_TIMEOUT_SECONDS=300"

$urls = Wait-ForBothQuickTunnelUrls -ApiTunnelLog $ApiTunnelLog -WebTunnelLog $WebTunnelLog -TimeoutSeconds $tunnelDeadline
$ApiPublic = $urls.Api
$WebPublic = $urls.Web

Write-Host ""
Write-Host "==== PUBLIC URLS ===="
Write-Host "Web URL: $WebPublic"
Write-Host "API URL: $ApiPublic"
Write-Host "====================="
Write-Host ""

if (-not $WebPublic -or -not $ApiPublic) {
    Write-Warning "Could not detect one/both Quick Tunnel URLs. Check logs in $RuntimeDir (api.trycloudflare.com in logs is the registrar, not your tunnel hostname)."
    try {
        $apiLogText = Get-Content -Path $ApiTunnelLog -Raw -ErrorAction Stop
        if ($apiLogText -like '*failed to request quick Tunnel*') {
            Write-Warning "tunnel-api.log reports quick-tunnel registration failure — often VPN/firewall/network blocking https://api.trycloudflare.com."
        }
    } catch {
        # ignore missing log
    }
} else {
    # Team B only needs web URL; API URL is entered in UI settings.
    Write-Host "Team B should open: $WebPublic"
    Write-Host "In web UI settings, set API base URL to: $ApiPublic"
}

Write-Host ""
Write-Host "Logs: $RuntimeDir"
Write-Host "To stop all processes, run stop-quick-tunnel.ps1"
