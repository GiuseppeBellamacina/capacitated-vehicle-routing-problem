param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("upload", "download", "download-results", "download-imgs", "push", "pull")]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$Path  # relative path for push/pull (e.g. "backend/cvrp/hga.py" or "cluster/")
)

$CLUSTER_USER = "bllgpp02h24c351g"
$CLUSTER_HOST = "gcluster.dmi.unict.it"
$REMOTE  = "${CLUSTER_USER}@${CLUSTER_HOST}:~/capacitated-vehicle-routing-problem"
$SSH_TARGET = "${CLUSTER_USER}@${CLUSTER_HOST}"
$LOCAL   = $PSScriptRoot

# Helper function per convertire CRLF in LF sul cluster
function Fix-RemoteLineEndings {
    param([string]$TargetDir = "~/capacitated-vehicle-routing-problem")
    Write-Host "  -> Converting DOS line breaks to UNIX (CRLF -> LF)..." -ForegroundColor Gray
    # Cerca script bash, python e configurazioni per rimuovere il \r (carriage return)
    $cmd = "find $TargetDir -type f \( -name '*.sh' -o -name '*.py' -o -name '*.toml' \) -exec sed -i 's/\r$//' {} +"
    ssh $SSH_TARGET $cmd
}

# ══════════════════════════════════════════════════════════════════════════════
# Upload: sends project to cluster via SCP
# ══════════════════════════════════════════════════════════════════════════════
function Upload {
    Write-Host "Uploading CVRP project to cluster..." -ForegroundColor Cyan

    # Clean __pycache__ before upload
    Write-Progress -Activity "Upload" -Status "Cleaning __pycache__..." -PercentComplete 0
    Get-ChildItem -Path $LOCAL -Directory -Recurse -Filter "__pycache__" | 
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # Ensure remote directory structure exists
    Write-Progress -Activity "Upload" -Status "Creating remote directories..." -PercentComplete 2
    ssh $SSH_TARGET "mkdir -p ~/capacitated-vehicle-routing-problem/{backend/cvrp,config,instances,cluster,results,docs/report/imgs}"

    # Files/directories to upload
    $items = @(
        "backend/cvrp",
        "backend/pyproject.toml",
        "backend/main.py",
        "backend/run_experiments.py",
        "backend/tune_parameters.py",
        "backend/plot_convergence.py",
        "backend/format_latex.py",
        "config/config_optuna.yaml",
        "instances",
        "cluster"
    )

    # Build flat list of (localPath, remotePath) pairs
    $files = [System.Collections.Generic.List[object]]::new()
    $dirsToClean = [System.Collections.Generic.List[string]]::new()

    foreach ($item in $items) {
        $localPath = Join-Path $LOCAL $item
        if (-not (Test-Path $localPath)) {
            Write-Host "  [SKIP] $item (not found)" -ForegroundColor Yellow
            continue
        }
        if (Test-Path $localPath -PathType Container) {
            $parent = Split-Path $item
            if (-not $parent) {
                $dirsToClean.Add($item)
            }
            Get-ChildItem -Path $localPath -File -Recurse | ForEach-Object {
                $relPath = $_.FullName.Substring($LOCAL.Length + 1) -replace '\\', '/'
                $files.Add(@{ Local = $_.FullName; Remote = $relPath })
            }
        } else {
            $files.Add(@{ Local = $localPath; Remote = $item })
        }
    }

    # Clean remote top-level dirs before uploading
    if ($dirsToClean.Count -gt 0) {
        $rmCmd = ($dirsToClean | ForEach-Object { "rm -rf ~/capacitated-vehicle-routing-problem/$_" }) -join "; "
        ssh $SSH_TARGET $rmCmd
        $mkCmd = ($dirsToClean | ForEach-Object { "mkdir -p ~/capacitated-vehicle-routing-problem/$_" }) -join "; "
        ssh $SSH_TARGET $mkCmd
    }

    # Ensure all remote subdirectories exist (batch)
    $remoteDirs = $files | ForEach-Object {
        $d = (Split-Path $_.Remote) -replace '\\', '/'
        if ($d) { "~/capacitated-vehicle-routing-problem/$d" }
    } | Sort-Object -Unique
    if ($remoteDirs.Count -gt 0) {
        $mkdirCmd = "mkdir -p " + ($remoteDirs -join " ")
        ssh $SSH_TARGET $mkdirCmd
    }

    # Upload files one by one with granular progress
    $total = $files.Count
    for ($i = 0; $i -lt $total; $i++) {
        $f = $files[$i]
        $pct = [int](($i / $total) * 100)
        $name = $f.Remote
        Write-Progress -Activity "Upload" `
            -Status "[$($i + 1)/$total] $name" `
            -PercentComplete $pct

        scp -q $f.Local "${REMOTE}/$($f.Remote)"
    }

    Write-Progress -Activity "Upload" -Completed
    
    # Fix CRLF issues per SLURM
    Fix-RemoteLineEndings

    Write-Host "Upload complete ($total files)." -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════════════════
# Download functions
# ══════════════════════════════════════════════════════════════════════════════
function DownloadAll {
    Write-Host "Downloading all outputs from cluster..." -ForegroundColor Cyan
    DownloadResults
    DownloadImgs
    Write-Host "Download complete." -ForegroundColor Green
}

function DownloadResults {
    Write-Host "  [1/2] results/ (all JSON + comparison table)..." -ForegroundColor Gray
    New-Item -ItemType Directory -Force -Path (Join-Path $LOCAL "results") | Out-Null
    ssh $SSH_TARGET "cd ~/capacitated-vehicle-routing-problem && tar cf - results/" | tar xvf - -C "$LOCAL"
    Write-Host "  -> saved to results/ (including config_*/results.json)" -ForegroundColor Gray
}

function DownloadImgs {
    Write-Host "  [2/2] docs/report/imgs/ (plots)..." -ForegroundColor Gray
    $dest = Join-Path $LOCAL "docs/report/imgs"
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    ssh $SSH_TARGET "cd ~/capacitated-vehicle-routing-problem && tar cf - docs/report/imgs" | tar xvf - -C "$LOCAL"
    Write-Host "  -> saved to docs/report/imgs/" -ForegroundColor Gray
}

# ══════════════════════════════════════════════════════════════════════════════
# Push/Pull single file or directory
# ══════════════════════════════════════════════════════════════════════════════
function Push {
    if (-not $Path) {
        Write-Host "Usage: .\sync_cluster.ps1 -Action push -Path <file-or-folder>" -ForegroundColor Red
        return
    }
    $localPath = Join-Path $LOCAL $Path
    if (-not (Test-Path $localPath)) {
        Write-Host "Not found: $Path" -ForegroundColor Red
        return
    }
    $remotePath = $Path -replace '\\', '/'
    $remoteDir = ($remotePath | Split-Path) -replace '\\', '/'
    if ($remoteDir) {
        ssh $SSH_TARGET "mkdir -p ~/capacitated-vehicle-routing-problem/$remoteDir"
    }
    if (Test-Path $localPath -PathType Container) {
        ssh $SSH_TARGET "mkdir -p ~/capacitated-vehicle-routing-problem/$remotePath"
        scp -rq "$localPath/." "${REMOTE}/$remotePath/"
    } else {
        scp -q $localPath "${REMOTE}/$remotePath"
    }
    
    # Fix CRLF per SLURM anche per i push singoli (per sicurezza formatta tutto o il file specifico)
    if (Test-Path $localPath -PathType Container) {
        Fix-RemoteLineEndings -TargetDir "~/capacitated-vehicle-routing-problem/$remotePath"
    } elseif ($remotePath -match "\.(sh|py|toml)$") {
        ssh $SSH_TARGET "sed -i 's/\r$//' ~/capacitated-vehicle-routing-problem/$remotePath"
    }

    Write-Host "Pushed $Path -> cluster" -ForegroundColor Green
}

function Pull {
    if (-not $Path) {
        Write-Host "Usage: .\sync_cluster.ps1 -Action pull -Path <file-or-folder>" -ForegroundColor Red
        return
    }
    $remotePath = $Path -replace '\\', '/'
    $localPath = Join-Path $LOCAL $Path
    $localDir = Split-Path $localPath
    if ($localDir) {
        New-Item -ItemType Directory -Force -Path $localDir | Out-Null
    }
    scp -rq "${REMOTE}/$remotePath" $localPath
    Write-Host "Pulled $Path <- cluster" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════════════════════
# Dispatch
# ══════════════════════════════════════════════════════════════════════════════
switch ($Action) {
    "upload"           { Upload }
    "download"         { DownloadAll }
    "download-results" { DownloadResults }
    "download-imgs"    { DownloadImgs }
    "push"             { Push }
    "pull"             { Pull }
}