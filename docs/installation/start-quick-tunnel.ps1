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

function Wait-ForUrlInLog {
    <#
    .SYNOPSIS
    Waits for a trycloudflare.com URL to appear in a cloudflared log.

    .PARAMETER LogPath
    Log file to scan.

    .PARAMETER TimeoutSeconds
    Max wait duration.
    #>
    param(
        [string]$LogPath,
        [int]$TimeoutSeconds = 45
    )

    # Poll until timeout for tunnel URL emission.
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $LogPath) {
            # Capture latest URL match from current log contents.
            $line = Select-String -Path $LogPath -Pattern 'https://[a-zA-Z0-9\.-]+\.trycloudflare\.com' -AllMatches -ErrorAction SilentlyContinue |
                Select-Object -Last 1
            if ($line -and $line.Matches.Count -gt 0) {
                return $line.Matches[0].Value
            }
        }
        Start-Sleep -Milliseconds 700  # Keep polling lightweight.
    }
    return $null
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

# Set local web origin for API CORS.
$env:CLIMATE_API_CORS_ORIGINS = "http://127.0.0.1:$WebPort"

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

Write-Host ""
Write-Host "Waiting for tunnel URLs..."

# Read generated public URLs from tunnel logs.
$ApiPublic = Wait-ForUrlInLog -LogPath $ApiTunnelLog
$WebPublic = Wait-ForUrlInLog -LogPath $WebTunnelLog

Write-Host ""
Write-Host "==== PUBLIC URLS ===="
Write-Host "Web URL: $WebPublic"
Write-Host "API URL: $ApiPublic"
Write-Host "====================="
Write-Host ""

if (-not $WebPublic -or -not $ApiPublic) {
    # Tell operator exactly where diagnostics live.
    Write-Warning "Could not detect one/both URLs yet. Check logs in $RuntimeDir"
} else {
    # Team B only needs web URL; API URL is entered in UI settings.
    Write-Host "Team B should open: $WebPublic"
    Write-Host "In web UI settings, set API base URL to: $ApiPublic"
}

Write-Host ""
Write-Host "Logs: $RuntimeDir"
Write-Host "To stop all processes, run stop-quick-tunnel.ps1"
