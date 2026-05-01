param(
    [string]$SuperUser = "postgres",
    [string]$SuperPassword = "postgres",
    [string]$AppDatabase = "xid_go",
    [string]$AppUser = "xid_user",
    [string]$AppPassword = "xid_password",
    [string]$PgHost = "localhost",
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SchemaFiles = @(
    (Join-Path $ProjectRoot "sql\schema\001_raw_betting_transactions.sql"),
    (Join-Path $ProjectRoot "sql\schema\002_stage_support.sql"),
    (Join-Path $ProjectRoot "sql\transformations\001_stage_bookmaker_bets_clean.sql"),
    (Join-Path $ProjectRoot "sql\transformations\002_core_views.sql"),
    (Join-Path $ProjectRoot "sql\validation_checks\001_quality_views.sql"),
    (Join-Path $ProjectRoot "sql\reporting\001_eod_reconciliation_views.sql"),
    (Join-Path $ProjectRoot "sql\reporting\002_alert_views.sql")
)

function Get-PsqlPath {
    $psql = Get-Command psql -ErrorAction SilentlyContinue
    if ($psql) {
        return $psql.Source
    }

    $postgresRoot = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1

    if (-not $postgresRoot) {
        throw "Could not find a PostgreSQL installation."
    }

    $candidate = Join-Path $postgresRoot.FullName "bin\psql.exe"
    if (-not (Test-Path $candidate)) {
        throw "Could not find psql.exe under $($postgresRoot.FullName)."
    }

    return $candidate
}

function Invoke-Psql {
    param(
        [string]$PsqlPath,
        [string]$Database,
        [string]$User,
        [string]$Password,
        [string[]]$ExtraArgs
    )

    $env:PGPASSWORD = $Password
    & $PsqlPath -v ON_ERROR_STOP=1 -h $PgHost -p $Port -U $User -d $Database @ExtraArgs
    if ($LASTEXITCODE -ne 0) {
        throw "psql command failed against database '$Database'."
    }
}

$psqlPath = Get-PsqlPath
Write-Host "Using psql at $psqlPath"

$roleExists = Invoke-Psql -PsqlPath $psqlPath -Database "postgres" -User $SuperUser -Password $SuperPassword -ExtraArgs @(
    "-tAc",
    "select 1 from pg_roles where rolname = '$AppUser';"
)

if ([string]::IsNullOrWhiteSpace($roleExists)) {
    Write-Host "Creating application role '$AppUser'"
    Invoke-Psql -PsqlPath $psqlPath -Database "postgres" -User $SuperUser -Password $SuperPassword -ExtraArgs @(
        "-c",
        "create role $AppUser login password '$AppPassword';"
    )
} else {
    Write-Host "Role '$AppUser' already exists"
}

$databaseExists = Invoke-Psql -PsqlPath $psqlPath -Database "postgres" -User $SuperUser -Password $SuperPassword -ExtraArgs @(
    "-tAc",
    "select 1 from pg_database where datname = '$AppDatabase';"
)

if ([string]::IsNullOrWhiteSpace($databaseExists)) {
    Write-Host "Creating database '$AppDatabase'"
    Invoke-Psql -PsqlPath $psqlPath -Database "postgres" -User $SuperUser -Password $SuperPassword -ExtraArgs @(
        "-c",
        "create database $AppDatabase owner $AppUser;"
    )
} else {
    Write-Host "Database '$AppDatabase' already exists"
}

foreach ($schemaFile in $SchemaFiles) {
    if (-not (Test-Path $schemaFile)) {
        throw "Required SQL file not found: $schemaFile"
    }

    Write-Host "Applying $(Split-Path $schemaFile -Leaf)"
    Invoke-Psql -PsqlPath $psqlPath -Database $AppDatabase -User $AppUser -Password $AppPassword -ExtraArgs @(
        "-f",
        $schemaFile
    )
}

Write-Host "Local PostgreSQL bootstrap complete."
