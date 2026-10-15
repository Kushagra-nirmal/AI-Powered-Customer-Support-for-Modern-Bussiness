# Server Launcher for Windows
Param(
    [string]$Port = "8000",
    [string]$HostAddress = "0.0.0.0",
    [string]$Env = "development"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting Production-Grade Agentic System ($Env) " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# Set environment variables
$env:APP_ENV = $Env
$env:PORT = $Port
$env:HOST = $HostAddress

# Check virtual environment
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $ScriptDir ".venv\Scripts\uvicorn.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Error: Virtual environment not found at $VenvPython" -ForegroundColor Red
    Write-Host "Please run setup first." -ForegroundColor Yellow
    exit 1
}

# Check if PostgreSQL server is running
$PgPort = 5433
$PgData = Join-Path $ScriptDir "pgdata"
$PgRunning = $false

$PgCtl = "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe"
if (Test-Path $PgCtl) {
    $statusOut = & $PgCtl -D $PgData status 2>&1
    if ($statusOut -match "server is running") {
        $PgRunning = $true
    }
}

if (-not $PgRunning) {
    Write-Host "Starting local PostgreSQL instance on port $PgPort..." -ForegroundColor Yellow
    if (Test-Path $PgData) {
        $PidFile = Join-Path $PgData "postmaster.pid"
        if (Test-Path $PidFile) {
            try {
                $OldPid = (Get-Content $PidFile -TotalCount 1).Trim()
                if ($OldPid -and -not (Get-Process -Id [int]$OldPid -ErrorAction SilentlyContinue)) {
                    Write-Host "Cleaning up stale postmaster.pid (PID $OldPid)..." -ForegroundColor Yellow
                    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                }
            } catch {}
        }
        & $PgCtl -D $PgData -l "$PgData\server.log" -o "-p $PgPort" start
        Start-Sleep -Seconds 2
    }
}
Write-Host "PostgreSQL is reachable on port $PgPort." -ForegroundColor Green

# Check if API server is already running on target port
$ApiTcp = New-Object System.Net.Sockets.TcpClient
$ApiConnect = $ApiTcp.BeginConnect("127.0.0.1", [int]$Port, $null, $null)
$ApiWait = $ApiConnect.AsyncWaitHandle.WaitOne(1000, $false)

if ($ApiWait) {
    $ApiTcp.EndConnect($ApiConnect)
    $ApiTcp.Close()
    Write-Host "`n==========================================================" -ForegroundColor Green
    Write-Host " Server is ALREADY RUNNING and healthy on port $Port!" -ForegroundColor Green
    Write-Host " Open the customer support app: http://127.0.0.1:$Port/" -ForegroundColor Cyan
    Write-Host " API documentation:          http://127.0.0.1:$Port/docs" -ForegroundColor DarkCyan
    Write-Host "==========================================================" -ForegroundColor Green
    exit 0
}

Write-Host "Launching SupportAI on http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host "API documentation: http://127.0.0.1:$Port/docs" -ForegroundColor DarkCyan
& $VenvPython run.py


