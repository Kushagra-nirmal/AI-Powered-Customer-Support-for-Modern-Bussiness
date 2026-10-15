# ==============================================================================
# Production-Grade Agentic System - Global Public Deployment Launcher
# Creator & Administrator: Nirmal Sharma
# ==============================================================================
Param(
    [string]$Port = "8000",
    [string]$HostAddress = "0.0.0.0"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "   🚀 LAUNCHING SUPPORTAI & JARVIS GLOBAL PUBLIC DEPLOYMENT       " -ForegroundColor Green
Write-Host "   Administrator: Nirmal Sharma                                   " -ForegroundColor Yellow
Write-Host "==================================================================`n" -ForegroundColor Cyan

# 1. Start local PostgreSQL if not running
$PgPort = 5433
$TcpClient = New-Object System.Net.Sockets.TcpClient
$Connect = $TcpClient.BeginConnect("127.0.0.1", $PgPort, $null, $null)
$Wait = $Connect.AsyncWaitHandle.WaitOne(1000, $false)

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
        & "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D $PgData -l "$PgData\server.log" -o "-p $PgPort" start
        Start-Sleep -Seconds 2
    }
} else {
    $TcpClient.EndConnect($Connect)
    $TcpClient.Close()
    Write-Host "[1/3] PostgreSQL database active on port $PgPort." -ForegroundColor Green
}

# 2. Check or launch Backend server on port 8000
$ApiTcp = New-Object System.Net.Sockets.TcpClient
$ApiConn = $ApiTcp.BeginConnect("127.0.0.1", [int]$Port, $null, $null)
$ApiWait = $ApiConn.AsyncWaitHandle.WaitOne(1000, $false)

if (-not $ApiWait) {
    Write-Host "[2/3] Starting SupportAI Backend server on port $Port..." -ForegroundColor Yellow
    $VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
    Start-Process -FilePath $VenvPython -ArgumentList "run.py" -WorkingDirectory $ScriptDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    $ApiTcp.EndConnect($ApiConn)
    $ApiTcp.Close()
    Write-Host "[2/3] Backend server active on port $Port." -ForegroundColor Green
}

# 3. Check or launch Cloudflare Tunnel
Write-Host "[3/3] Checking Global HTTPS Cloudflare Tunnel..." -ForegroundColor Yellow
$Cloudflared = Join-Path $ScriptDir "cloudflared.exe"
$TunnelLog = Join-Path $ScriptDir "tunnel.log"

$ExistingCf = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if (-not $ExistingCf) {
    Write-Host "Starting new Cloudflare Tunnel daemon..." -ForegroundColor Yellow
    if (Test-Path $TunnelLog) { Remove-Item $TunnelLog -Force -ErrorAction SilentlyContinue }
    Start-Process -FilePath $Cloudflared -ArgumentList "tunnel --url http://127.0.0.1:$Port --logfile $TunnelLog" -WorkingDirectory $ScriptDir -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# Extract Public URL
$PublicUrl = ""
if (Test-Path $TunnelLog) {
    $Match = Select-String -Path $TunnelLog -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com"
    if ($Match) {
        $PublicUrl = $Match.Matches[0].Value
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
    Start-Process $PublicUrl
} else {
    Write-Host "`nTunnel active! Check tunnel.log for the URL: http://127.0.0.1:$Port`n" -ForegroundColor Yellow
}
