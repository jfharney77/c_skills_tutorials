# run.ps1 — Start the Research Paper Analyzer on Windows
# Usage: .\run.ps1
# Requires: Python 3.10+ on PATH, Ollama running on Windows

param(
    [int]$Port = 8000,
    [string]$OllamaHost = "http://localhost:11434"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Run from V1 project root, not scripts/
Set-Location (Split-Path -Parent $ScriptDir)

Write-Host ""
Write-Host "=== Research Paper Analyzer ===" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python ────────────────────────────────────────────────────────────
try {
    $pyVersion = python --version 2>&1
    Write-Host "Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# ── 2. Create virtualenv if needed ────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

$pip    = ".\.venv\Scripts\pip.exe"
$python = ".\.venv\Scripts\python.exe"
$uvicorn = ".\.venv\Scripts\uvicorn.exe"

# ── 3. Install / sync dependencies ────────────────────────────────────────────
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed." -ForegroundColor Red
    exit 1
}
Write-Host "Dependencies OK" -ForegroundColor Green

# ── 4. Check Ollama ───────────────────────────────────────────────────────────
Write-Host "Checking Ollama at $OllamaHost ..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$OllamaHost" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "Ollama is running" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "WARNING: Could not reach Ollama at $OllamaHost" -ForegroundColor Yellow
    Write-Host "Make sure 'ollama serve' is running in another terminal." -ForegroundColor Yellow
    Write-Host ""
}

# ── 5. Launch server ──────────────────────────────────────────────────────────
$env:OLLAMA_HOST = $OllamaHost

Write-Host ""
Write-Host "Starting server on http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# Open browser after a short delay (background job)
Start-Job -ScriptBlock {
    param($port)
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:$port"
} -ArgumentList $Port | Out-Null

& $uvicorn app.main:app --port $Port --reload
