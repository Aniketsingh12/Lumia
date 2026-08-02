# BotForge — local launcher for Windows
# Runs backend (FastAPI) + frontend (Vite) in separate windows.
# Requires: Python 3.11+, Node.js 18+ on PATH.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "BotForge launcher" -ForegroundColor Cyan
Write-Host "================="

# --- Sanity checks ---
function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$cmd' not found on PATH. $hint" -ForegroundColor Red
        exit 1
    }
}
Need "python" "Install Python 3.11+ from https://www.python.org/downloads/"
Need "node"   "Install Node.js 18+ from https://nodejs.org/"
Need "npm"    "Install Node.js 18+ from https://nodejs.org/"

# --- .env files ---
if (-not (Test-Path "$root\backend\.env")) {
    Copy-Item "$root\backend\.env.example" "$root\backend\.env"
    Write-Host "Created backend\.env (edit it to add your LLM keys)" -ForegroundColor Yellow
}
if (-not (Test-Path "$root\frontend\.env")) {
    Copy-Item "$root\frontend\.env.example" "$root\frontend\.env"
    Write-Host "Created frontend\.env" -ForegroundColor Yellow
}

# --- Backend: venv + deps ---
$venv = "$root\backend\.venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv "$venv"
}
Write-Host "Installing backend dependencies (first run can take a few minutes)..." -ForegroundColor Yellow
& "$venv\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
& "$venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt"

# --- Frontend deps ---
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    npm install
    Pop-Location
}

# --- Launch in two new PowerShell windows ---
Write-Host ""
Write-Host "Launching backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; & '$venv\Scripts\Activate.ps1'; uvicorn app.main:app --reload --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "Launching frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev"
)

Start-Sleep -Seconds 5
Write-Host ""
Write-Host "BotForge should be starting:" -ForegroundColor Green
Write-Host "  Dashboard:  http://localhost:5173"
Write-Host "  API docs:   http://localhost:8000/docs"
Write-Host ""
Write-Host "Close the two new PowerShell windows to stop." -ForegroundColor DarkGray
Start-Process "http://localhost:5173"
