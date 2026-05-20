<#
.SYNOPSIS
Stops all processes started by start-quick-tunnel.ps1.

.DESCRIPTION
Reads PID files from .quick-tunnel-runtime and force-stops each process if alive.
Removes PID files afterward so next startup begins cleanly.
#>

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

# Runtime folder shared with start script.
$RuntimeDir = Join-Path $RepoRoot ".quick-tunnel-runtime"

# PID files tracked for API, web, and both tunnels.
$pidFiles = @("api.pid","web.pid","tunnel-api.pid","tunnel-web.pid") |
    ForEach-Object { Join-Path $RuntimeDir $_ }

foreach ($f in $pidFiles) {
    if (Test-Path $f) {
        # Read recorded process ID.
        $procId = Get-Content $f
        if ($procId) {
            try {
                # Force-stop to ensure background child shells are terminated.
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "Stopped PID $procId"
            } catch {
                # Process may already be gone; keep cleanup idempotent.
                Write-Host "PID $procId not running."
            }
        }
        # Remove PID file even if process was already stopped.
        Remove-Item $f -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Done."
