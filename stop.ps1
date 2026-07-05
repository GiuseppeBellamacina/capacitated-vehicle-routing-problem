#!/usr/bin/env pwsh
# Stop the CVRP HGA Solver (backend + frontend)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CVRP Solver — Shutdown" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop Backend (port 8000)
Write-Host "Stopping Backend (port 8000)..." -ForegroundColor Yellow
$backendPid = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($backendPid) {
    foreach ($procId in $backendPid) {
        if ($procId -eq 0) { continue }
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $procId -Force
                Write-Host "  Stopped $($proc.ProcessName) (PID $procId)" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Could not stop PID $procId" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  No process found on port 8000" -ForegroundColor Gray
}

Write-Host ""

# Stop Frontend (port 3000)
Write-Host "Stopping Frontend (port 3000)..." -ForegroundColor Yellow
$frontendPid = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($frontendPid) {
    foreach ($procId in $frontendPid) {
        if ($procId -eq 0) { continue }
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $procId -Force
                Write-Host "  Stopped $($proc.ProcessName) (PID $procId)" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Could not stop PID $procId" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  No process found on port 3000" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Shutdown completed" -ForegroundColor Green
