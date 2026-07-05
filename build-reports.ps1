#!/usr/bin/env pwsh
# Build both LaTeX reports (full + compact) with clean → pdflatex → bibtex → pdflatex × 2

$ROOT = $PSScriptRoot
if ([string]::IsNullOrEmpty($ROOT)) { $ROOT = $PWD.Path }

$reports = @(
    @{ Name = "Full Report"; Dir = "$ROOT\docs\report" },
    @{ Name = "Compact Report"; Dir = "$ROOT\docs\report-compact" }
)

function Build-Report {
    param($Name, $Dir)

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Building $Name" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    Push-Location $Dir
    try {

    # 1. Clean auxiliary files
    Write-Host "Cleaning auxiliary files..." -ForegroundColor Yellow
    Remove-Item -Force -ErrorAction SilentlyContinue report.aux, report.bbl, report.blg, report.out, report.toc, report.lot, report.lof, report.run.xml, report-blx.bib, report.bcf, report.log

    # 2. First pdflatex pass
    Write-Host "pdflatex (pass 1)..." -ForegroundColor Gray
    $result = pdflatex -interaction=nonstopmode report.tex 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: pdflatex returned exit code $LASTEXITCODE" -ForegroundColor Yellow
    }

    # 3. BibTeX
    Write-Host "bibtex..." -ForegroundColor Gray
    bibtex report 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: bibtex returned exit code $LASTEXITCODE" -ForegroundColor Yellow
    }

    # 4. Second pdflatex pass
    Write-Host "pdflatex (pass 2)..." -ForegroundColor Gray
    pdflatex -interaction=nonstopmode report.tex 2>&1 | Out-Null

    # 5. Third pdflatex pass (finalize cross-references)
    Write-Host "pdflatex (pass 3 - final)..." -ForegroundColor Gray
    $result = pdflatex -interaction=nonstopmode report.tex 2>&1
    $last = $result | Select-Object -Last 5
    $last | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }

    # Check for undefined references (only catch specific "Reference `xxx' undefined" warnings,
    # not the generic biblatex "There were undefined references" message)
    $undefined = $result | Select-String "undefined on input line"
    if ($undefined) {
        Write-Host "  WARNING: Unresolved references:" -ForegroundColor Yellow
        $undefined | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
    } else {
        Write-Host "  All cross-references resolved" -ForegroundColor Green
    }

    # Show page count
    $pages = $result | Select-String "Output written on report.pdf \((\d+) pages"
    if ($pages) {
        Write-Host "  $($pages.Matches[0].Value.Trim())" -ForegroundColor Green
    }

    Write-Host ""
    } finally {
        Pop-Location
    }
}

# Build both reports
$totalStart = Get-Date

foreach ($report in $reports) {
    Build-Report -Name $report.Name -Dir $report.Dir
}

$elapsed = (Get-Date) - $totalStart
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All reports built in $($elapsed.TotalSeconds.ToString('0.0'))s" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
