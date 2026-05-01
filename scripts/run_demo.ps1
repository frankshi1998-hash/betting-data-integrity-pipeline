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

Invoke-Checked "Run Python unit tests" {
    & $Python -m pytest -q
}

$pipelineArgs = @(
    "-m", "src.orchestration.run_pipeline",
    "--demo",
    "--raw-dir", $DemoRawDir,
    "--output-dir", $OutputDir,
    "--replace-files",
    "--require-demo-alerts"
)

if ($SkipDbt) {
    $pipelineArgs += "--skip-dbt"
}

Invoke-Checked "Run orchestrated demo pipeline" {
    & $Python @pipelineArgs
}

Write-Host ""
Write-Host "Demo pipeline completed successfully."
Write-Host "Generated outputs: $OutputDir"
