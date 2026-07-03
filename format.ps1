# Format and lint all code with Isort, Black and Ruff
# Run from project root: .\format.ps1

$ErrorActionPreference = "Stop"

$BACKEND_DIR = Join-Path $PSScriptRoot "backend"

Write-Host "================================"
Write-Host "  Code Formatting & Linting"
Write-Host "  Project: CVRP Solver (HGA)"
Write-Host "================================"
Write-Host ""

# Run Isort
Write-Host "Running Isort..." -ForegroundColor Cyan
Push-Location $BACKEND_DIR
isort .
Pop-Location
Write-Host "Isort completed" -ForegroundColor Green

Write-Host ""

# Run Black
Write-Host "Running Black formatter..." -ForegroundColor Cyan
Push-Location $BACKEND_DIR
black .
Pop-Location
Write-Host "Black formatting completed" -ForegroundColor Green

Write-Host ""

# Run Ruff
Write-Host "Running Ruff linter with auto-fix..." -ForegroundColor Cyan
Push-Location $BACKEND_DIR
ruff check --fix .
Pop-Location
Write-Host "Ruff linting completed" -ForegroundColor Green

Write-Host ""
Write-Host "================================"
Write-Host "  Formatting Complete!"
Write-Host "================================"
