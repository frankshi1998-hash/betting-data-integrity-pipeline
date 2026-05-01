# xid_go dbt Project

This folder adds a production-style dbt layer on top of the local PostgreSQL pipeline.

It reads from:

- `raw.bookmaker_bet_dump`

And builds:

- staging models for typed parsing
- marts models for customers, events, bets, and payouts
- quality models for validation issues
- reporting models for EOD reconciliation, alerts, and anomaly scorecards

Run commands:

```powershell
$envFile = Get-Content ..\.env
foreach ($line in $envFile) {
    if ($line -match '^(.*?)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
}
..\.venv\Scripts\dbt.exe debug --project-dir . --profiles-dir .\profiles
..\.venv\Scripts\dbt.exe run --project-dir . --profiles-dir .\profiles
..\.venv\Scripts\dbt.exe test --project-dir . --profiles-dir .\profiles
```
