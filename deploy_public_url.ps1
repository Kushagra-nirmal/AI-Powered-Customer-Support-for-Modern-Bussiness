# ==============================================================================
# Production-Grade Agentic System - Global Public Deployment Launcher
# Creator & Administrator: Nirmal Sharma
# ==============================================================================
Param(
    [string]$Port = "8000",
    [string]$HostAddress = "0.0.0.0",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-TcpPort {
    Param(
        [string]$Address,
        [int]$PortNumber,
        [int]$TimeoutMilliseconds = 1000
    )

    $Client = New-Object System.Net.Sockets.TcpClient
    try {
        $Connect = $Client.BeginConnect($Address, $PortNumber, $null, $null)
        if (-not $Connect.AsyncWaitHandle.WaitOne($TimeoutMilliseconds, $false)) {
            return $false
        }
        $Client.EndConnect($Connect)
        return $true
    } catch {
        return $false
    } finally {
        $Client.Close()
    }
}

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "   🚀 LAUNCHING SUPPORTAI & JARVIS GLOBAL PUBLIC DEPLOYMENT       " -ForegroundColor Green
Write-Host "   Administrator: Nirmal Sharma                                   " -ForegroundColor Yellow
Write-Host "==================================================================`n" -ForegroundColor Cyan

# 1. Start local PostgreSQL if not running
$PgPort = 5433
$Wait = Test-TcpPort -Address "127.0.0.1" -PortNumber $PgPort

if (-not $Wait) {
    Write-Host "[1/3] Starting local PostgreSQL database on port $PgPort..." -ForegroundColor Yellow
    $PgData = Join-Path $ScriptDir "pgdata"
    if (Test-Path $PgData) {
        $PidFile = Join-Path $PgData "postmaster.pid"
        if (Test-Path $PidFile) {
            try {
                $OldPid = (Get-Content $PidFile -TotalCount 1).Trim()
                if ($OldPid -and -not (Get-Process -Id [int]$OldPid -ErrorAction SilentlyContinue)) {
                    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
        $PgLog = Join-Path $env:TEMP "production-agentic-postgres.log"
        & "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D $PgData -l $PgLog -o "-p $PgPort" start
        Start-Sleep -Seconds 2
    }
} else {
    Write-Host "[1/3] PostgreSQL database active on port $PgPort." -ForegroundColor Green
}

# 2. Check or launch Backend server
$TargetPort = [int]$Port
$ApiWait = Test-TcpPort -Address "127.0.0.1" -PortNumber $TargetPort
if ($ApiWait) {
    try {
        $Probe = Invoke-WebRequest "http://127.0.0.1:$TargetPort/health" -UseBasicParsing -TimeoutSec 2
        if ($Probe.Content -match "genesis-shadow") {
            Write-Host "Port $TargetPort is hosting Genesis Shadow. Using port 8001 for SupportAI..." -ForegroundColor Yellow
            $Port = "8001"
            $TargetPort = 8001
            $ApiWait = Test-TcpPort -Address "127.0.0.1" -PortNumber $TargetPort
        }
    } catch {}
}

if (-not $ApiWait) {
    Write-Host "[2/3] Starting SupportAI Backend server on port $Port..." -ForegroundColor Yellow
    $PythonCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Temp\production-agentic-system-venv\Scripts\python.exe"),
        (Join-Path $ScriptDir ".venv\Scripts\python.exe"),
        (Join-Path $ScriptDir ".venv313\Scripts\python.exe")
    )
    $VenvPython = $PythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $VenvPython) {
        Write-Host "No usable Python environment found." -ForegroundColor Red
        exit 1
    }
    $env:APP_ENV = "development"
    $env:PORT = $Port
    $env:HOST = $HostAddress
    $ApiLog = Join-Path $env:TEMP "production-agentic-api.log"
    $ApiErrorLog = Join-Path $env:TEMP "production-agentic-api.err.log"
    Start-Process -FilePath $VenvPython -ArgumentList "run.py" -WorkingDirectory $ScriptDir -WindowStyle Hidden -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErrorLog
    $Healthy = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $Health = Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
            if ($Health.StatusCode -eq 200) { $Healthy = $true; break }
        } catch {}
    }
    if (-not $Healthy) {
        Write-Host "Backend failed to become healthy. See $ApiErrorLog" -ForegroundColor Red
        exit 1
    }
} else {
    try {
        $Health = Invoke-WebRequest "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
        if ($Health.StatusCode -ne 200) { throw "Health endpoint returned HTTP $($Health.StatusCode)" }
        Write-Host "[2/3] Backend server active on port $Port." -ForegroundColor Green
    } catch {
        Write-Host "Backend port $Port is open but /health is unavailable. Stop the conflicting process and retry." -ForegroundColor Red
        exit 1
    }
}

# 3. Check or launch Cloudflare Tunnel
Write-Host "[3/3] Checking Global HTTPS Cloudflare Tunnel..." -ForegroundColor Yellow
$Cloudflared = Join-Path $ScriptDir "cloudflared.exe"
$TunnelLog = Join-Path $ScriptDir "tunnel.log"

$ExistingCf = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $Cloudflared }
if ($ExistingCf) {
    Write-Host "Replacing the existing quick tunnel for port $Port..." -ForegroundColor Yellow
    $ExistingCf | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
} else {
    Write-Host "Starting new Cloudflare Tunnel daemon..." -ForegroundColor Yellow
}
if (Test-Path $TunnelLog) { Remove-Item $TunnelLog -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath $Cloudflared -ArgumentList "tunnel --url http://127.0.0.1:$Port --protocol http2 --edge-ip-version 4 --logfile $TunnelLog" -WorkingDirectory $ScriptDir -WindowStyle Hidden

# Extract Public URL
$PublicUrl = ""
for ($i = 0; $i -lt 30 -and -not $PublicUrl; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $TunnelLog) {
        $Matches = Select-String -Path $TunnelLog -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com"
        if ($Matches) {
            $PublicUrl = $Matches[-1].Matches[0].Value
        }
    }
}

if (-not $PublicUrl) {
    # Check default task log if running from daemon task
    $DefaultLogs = Get-ChildItem "C:\Users\01234\.gemini\antigravity-ide\brain\*\.system_generated\tasks\task-*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
    foreach ($logFile in $DefaultLogs) {
        $Match = Select-String -Path $logFile.FullName -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue
        if ($Match) {
            $PublicUrl = $Match.Matches[0].Value
            break
        }
    }
}

if ($PublicUrl) {
    Write-Host "`n==================================================================" -ForegroundColor Green
    Write-Host "   🎉 GLOBAL PUBLIC DEPLOYMENT URL READY!                         " -ForegroundColor Green
    Write-Host "   Use this URL on ANY smartphone, tablet, laptop, or PC:        " -ForegroundColor White
    Write-Host "   👉 $PublicUrl                                                  " -ForegroundColor Cyan
    Write-Host "==================================================================`n" -ForegroundColor Green
    if ($OpenBrowser) {
        Start-Process $PublicUrl
    }
} else {
    Write-Host "`nCloudflare Tunnel did not publish a URL. Check $TunnelLog for details.`n" -ForegroundColor Red
    exit 1
}
