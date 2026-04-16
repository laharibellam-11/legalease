# LexiChain - Complete Setup and Run Script
# This script installs all dependencies and starts all three services

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       LEXI-CHAIN - Complete Setup and Run Script         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Color functions
function Write-Success { Write-Host $args[0] -ForegroundColor Green }
function Write-Warning { Write-Host $args[0] -ForegroundColor Yellow }
function Write-Error { Write-Host $args[0] -ForegroundColor Red }
function Write-Info { Write-Host $args[0] -ForegroundColor Cyan }

# Step 1: Backend Setup
Write-Info "Step 1: Setting up BACKEND..."
Push-Location BACKEND
Write-Info "  Setting up Python Virtual Environment..."
python -m venv venv
# Activate logic that works safely in script context
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
Write-Success "  [x] Backend dependencies installed"
Pop-Location

# Step 2: Frontend Setup
Write-Info "Step 2: Setting up FRONTEND..."
Push-Location FRONTEND
Write-Info "  Installing Node dependencies..."
if (-Not (Test-Path node_modules)) {
    npm install --silent
} else {
    Write-Success "  [x] Frontend dependencies already installed"
}
Pop-Location

# Step 3: Admin Setup
Write-Info "Step 3: Setting up ADMIN..."
Push-Location ADMIN
Write-Info "  Installing Node dependencies..."
if (-Not (Test-Path node_modules)) {
    npm install --silent
} else {
    Write-Success "  [x] Admin dependencies already installed"
}
Pop-Location

Write-Host ""
Write-Success "==========================================================" -NoNewline
Write-Host ""
Write-Success "       [x] All Dependencies Installed Successfully        " -NoNewline
Write-Host ""
Write-Success "==========================================================" -NoNewline
Write-Host ""
Write-Host ""

Write-Info "Starting all services in parallel..."
Write-Warning "Note: Open these URLs in your browser:"
Write-Host ""
Write-Host "  * Backend API:      http://localhost:8000" -ForegroundColor Blue
Write-Host "    API Docs:         http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "  * Frontend:         http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "  * Admin Panel:      http://localhost:5174" -ForegroundColor Magenta
Write-Host ""
Write-Info "Press Ctrl+C to stop all services"
Write-Host ""

# Start Backend
Write-Info "Starting Backend (http://localhost:8000)..."
Start-Process -NoNewWindow -FilePath "BACKEND\venv\Scripts\python.exe" -ArgumentList "BACKEND\run.py"
Start-Sleep -Seconds 3

# Start Frontend
Write-Info "Starting Frontend (http://localhost:5173)..."
Start-Process -NoNewWindow -WorkingDirectory "FRONTEND" -FilePath "npm.cmd" -ArgumentList "run dev"
Start-Sleep -Seconds 2

# Start Admin
Write-Info "Starting Admin Panel (http://localhost:5174)..."
Start-Process -NoNewWindow -WorkingDirectory "ADMIN" -FilePath "npm.cmd" -ArgumentList "run dev"

Write-Success "[x] All services started!"
Write-Info "Windows will remain open. Press Ctrl+C in any window to stop that service."
