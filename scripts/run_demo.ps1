param(
    [string]$DemoRawDir,
    [string]$OutputDir,
    [switch]$SkipDocker,
    [switch]$SkipDbt
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not $DemoRawDir) {
    $DemoRawDir = Join-Path $ProjectRoot "ci_artifacts\demo_raw"
}

if (-not $OutputDir) {
    $OutputDir = Join-Path $ProjectRoot "ci_artifacts\demo_processed"
}

$Python = if (Test-Path ".\.venv\Scripts\python.exe") {
    ".\.venv\Scripts\python.exe"
} else {
    "python"
}

$Dbt = if (Test-Path ".\.venv\Scripts\dbt.exe") {
    ".\.venv\Scripts\dbt.exe"
} else {
    "dbt"
}

function Import-DotEnv {
    $envPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        return
    }

    foreach ($line in Get-Content $envPath) {
        if ($line -match "^\s*#" -or $line -notmatch "=") {
            continue
        }

        $name, $value = $line -split "=", 2
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
    }
}

function Invoke-Checked {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Label"
    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Label"
    }
}

function Test-PostgresPort {
    $hostName = if ($env:PGHOST) { $env:PGHOST } else { "localhost" }
    $port = if ($env:PGPORT) { [int]$env:PGPORT } else { 5432 }

    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $connect = $client.BeginConnect($hostName, $port, $null, $null)
        $connected = $connect.AsyncWaitHandle.WaitOne(1000, $false)
        if ($connected) {
            $client.EndConnect($connect)
        }
        $client.Close()
        return $connected
    } catch {
        return $false
    }
}

Import-DotEnv

if (-not $SkipDocker) {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker) {
        Invoke-Checked "Start PostgreSQL with Docker Compose" {
            docker compose up -d
        }
    } else {
        Write-Warning "Docker was not found. Continuing only if PostgreSQL is already running."
    }
}

if (-not (Test-PostgresPort)) {
    throw "PostgreSQL is not reachable. Start Docker Desktop or run PostgreSQL locally, then retry."
}

$demoWorkbookPath = Join-Path $DemoRawDir "demo_bookmaker_bet_dump.xlsx"

Invoke-Checked "Generate synthetic demo workbook" {
    & $Python -m src.data_generation.create_demo_workbook --output-path $demoWorkbookPath
}

Invoke-Checked "Run Python unit tests" {
    & $Python -m pytest -q
}

Invoke-Checked "Apply SQL pipeline" {
    & $Python -m src.setup.apply_sql_pipeline
}

Invoke-Checked "Load synthetic workbook into raw schema" {
    & $Python -m src.ingest.load_bookmaker_dump --raw-dir $DemoRawDir --replace-files
}

Invoke-Checked "Export reporting CSVs" {
    & $Python -m src.reporting.export_reporting_views --output-dir $OutputDir
}

if (-not $SkipDbt) {
    Invoke-Checked "dbt debug" {
        & $Dbt debug --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
    }

    Invoke-Checked "dbt run" {
        & $Dbt run --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
    }

    Invoke-Checked "dbt test" {
        & $Dbt test --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
    }
}

Write-Host ""
Write-Host "Demo pipeline completed successfully."
Write-Host "Generated outputs: $OutputDir"
