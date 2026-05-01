# Betting Data Integrity Pipeline

A production-style data engineering project for betting transaction integrity.

The pipeline ingests messy bookmaker Excel dumps, preserves the source data, transforms it into clean analytical models, runs data quality checks, and produces end-of-day reconciliation and alert outputs.

## Problem

Transactional betting systems can fail in ways that are painful for operations and finance teams:

- duplicated bet records
- negative or malformed stake values
- settlement and payout inconsistencies
- unreliable daily reconciliation numbers
- source files that arrive as messy operational exports instead of clean API events

This project shows how to design and implement a practical pipeline around those realities.

## Solution

The current version implements a complete local batch pipeline:

- lands raw monthly Excel workbooks into PostgreSQL
- keeps raw source columns intact for auditability
- parses dates, times, flags, money values, odds, payouts, and race details in a staging layer
- builds curated customer, event, bet, and payout views
- runs reusable data quality checks for duplicate bet keys, negative stakes, missing event timestamps, cancelled bets with payouts, and payouts without stakes
- produces daily reconciliation summaries and rule-based anomaly alerts
- mirrors the SQL model flow in dbt with tests
- exports reporting-ready CSV outputs

## Architecture

```text
Excel workbooks
  -> raw.bookmaker_bet_dump
  -> stage.bookmaker_bets_clean
  -> core.customers / core.events / core.bets / core.payouts
  -> quality.bookmaker_bet_validation_issues
  -> reporting.daily_reconciliation_summary / reporting.alert_feed
  -> CSV outputs
```

## Tech Stack

- Python
- PostgreSQL
- SQL
- dbt
- Docker
- pytest / unittest
- GitHub Actions

## Repository Layout

```text
data/
  raw/              Source data notes. Raw Excel files are ignored by Git.
  processed/        Local generated outputs. Ignored by Git.
  sample_outputs/   Redacted portfolio-safe output examples.
dbt_project/        dbt models and singular tests.
docs/               Source profiling notes.
scripts/            Local PostgreSQL bootstrap helper.
sql/                Raw schema, transforms, validation, and reporting views.
src/                Python ingestion, setup, config, and reporting export code.
tests/              Python unit tests.
```

## Sample Outputs

Portfolio-safe examples are included in `data/sample_outputs/`:

- `daily_reconciliation_summary_sample.csv`
- `daily_issue_summary_sample.csv`
- `alert_feed_sample.csv`

Full generated outputs are written locally to `data/processed/`:

- `daily_reconciliation_summary.csv`
- `daily_issue_summary.csv`
- `daily_bookmaker_summary.csv`
- `alert_feed.csv`
- `alert_summary.csv`

`data/processed/` is ignored because those files are reproducible outputs.

## Local Setup

For a quick end-to-end demo on Windows, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_demo.ps1
```

The demo script generates a synthetic workbook, applies the SQL pipeline, loads the workbook, exports reporting CSVs, and runs dbt checks. By default it writes generated demo files under `ci_artifacts/`, which is ignored by Git.

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` from the example:

```powershell
Copy-Item .env.example .env
```

If you do not have private source workbooks, generate a small synthetic workbook first:

```powershell
python -m src.data_generation.create_demo_workbook
```

Start PostgreSQL with Docker:

```powershell
docker compose up -d
```

Apply the SQL pipeline:

```powershell
python -m src.setup.apply_sql_pipeline
```

Validate the raw Excel files without loading them:

```powershell
python -m src.ingest.load_bookmaker_dump --dry-run
```

Load raw workbook data:

```powershell
python -m src.ingest.load_bookmaker_dump --replace-files
```

Export reporting outputs:

```powershell
python -m src.reporting.export_reporting_views
```

## dbt

The dbt project mirrors the raw-to-reporting model flow.

```powershell
.\.venv\Scripts\dbt.exe debug --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
.\.venv\Scripts\dbt.exe run --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
.\.venv\Scripts\dbt.exe test --project-dir .\dbt_project --profiles-dir .\dbt_project\profiles
```

The dbt models build into schemas such as:

- `analytics_dbt_stage`
- `analytics_dbt_core`
- `analytics_dbt_quality`
- `analytics_dbt_reporting`

## Validation Rules

Current rule-based checks include:

- duplicate `source_uuid` + `ticket_no` inside the same source file
- negative total stake after parsing win/place stake fields
- missing event timestamp
- cancelled bet with positive payout
- payout without stake
- duplicate ratio alert thresholds
- negative stake spike alert thresholds
- loss-day payout ratio alert thresholds

## Verification

Run Python tests:

```powershell
python -m pytest -q
```

The GitHub Actions workflow also validates the project against a clean PostgreSQL service by running:

- Python unit tests
- synthetic workbook generation
- SQL pipeline application
- demo workbook ingestion
- reporting export generation
- `dbt debug`
- `dbt parse`
- `dbt run`
- `dbt test`

## Project Status

Version 1 is now a complete local data integrity pipeline. The next valuable extensions would be:

- add a small anomaly scoring model after the rule-based alert layer
- add an orchestrator such as Prefect or Airflow
- add cloud storage ingestion with S3
