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
- calculates an explainable source-day anomaly scorecard for risk prioritization
- adds a lightweight ML anomaly model as a secondary triage signal
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
  -> reporting.anomaly_scorecard
  -> ML anomaly scores
  -> CSV outputs
```

## Tech Stack

- Python
- PostgreSQL
- SQL
- dbt
- Prefect
- scikit-learn
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
- `anomaly_scorecard_sample.csv`
- `ml_anomaly_scores_sample.csv`
- `ml_anomaly_report_sample.md`

Full generated outputs are written locally to `data/processed/`:

- `daily_reconciliation_summary.csv`
- `daily_issue_summary.csv`
- `daily_bookmaker_summary.csv`
- `alert_feed.csv`
- `alert_summary.csv`
- `anomaly_scorecard.csv`
- `eod_integrity_report.md`
- `ml_anomaly_scores.csv`
- `ml_anomaly_report.md`
- `pipeline_run_summary.json`

`data/processed/` is ignored because those files are reproducible outputs.

## Local Setup

For a quick end-to-end demo on Windows, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_demo.ps1
```

The demo script runs the Prefect-orchestrated pipeline. It generates a synthetic workbook, applies the SQL pipeline, loads the workbook, exports reporting CSVs, generates the Markdown reports, runs ML anomaly scoring, runs dbt checks, applies quality gates, and writes a run summary under `ci_artifacts/`, which is ignored by Git.

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

If you do not have private source workbooks, generate a synthetic demo workbook first:

```powershell
python -m src.data_generation.create_demo_workbook
```

The default demo workbook includes enough synthetic rows to trigger validation issues, source-day alerts, and anomaly scorecard risk bands.

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

Generate the Markdown EOD report:

```powershell
python -m src.reporting.generate_eod_report
```

Run the orchestrated pipeline directly:

```powershell
python -m src.orchestration.run_pipeline --demo --raw-dir ci_artifacts/orchestrated_raw --output-dir ci_artifacts/orchestrated_processed --replace-files --require-demo-alerts
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

## Anomaly Scorecard

The scorecard ranks each source file and reporting day from `0` to `100` using explainable components:

- duplicate bet pressure
- negative stake pressure
- payout loss pressure
- overall issue density
- alert severity

Each row receives a `risk_band`, `primary_driver`, and `recommended_action`, which turns validation results into a practical operations queue.

## ML Anomaly Model

The optional ML layer is implemented in `src.anomaly_detection.ml_anomaly_model`.

It trains a local unsupervised Isolation Forest over source-day reconciliation features such as rule anomaly score, duplicate pressure, issue density, payout ratio, alert volume, and net revenue movement.

The model writes:

- `ml_anomaly_scores.csv`
- `ml_anomaly_report.md`

This is intentionally a secondary triage signal, not a replacement for explainable data quality checks. The CSV keeps the rule-based anomaly score beside the ML score so reviewers can compare deterministic business logic with model-driven outlier detection.

## Orchestration

The production-style workflow is implemented with Prefect in `src.orchestration.run_pipeline`.

The flow coordinates:

- synthetic workbook generation
- raw ingestion
- SQL model application
- reporting exports
- Markdown EOD report generation
- ML anomaly scoring
- dbt debug, parse, run, and test
- quality gates for loaded rows, artifacts, anomaly rows, ML outliers, and demo alerts
- `pipeline_run_summary.json` output

## Verification

Run Python tests:

```powershell
python -m pytest -q
```

The GitHub Actions workflow also validates the project against a clean PostgreSQL service by running:

- Python unit tests
- the Prefect-orchestrated demo pipeline
- quality gates for demo alerts, critical anomaly scoring, and ML outlier scoring
- dbt debug, parse, run, and test inside the orchestrated flow

## Project Status

Version 1 is now a complete local data integrity pipeline. The next valuable extensions would be:

- add cloud storage ingestion with S3
- add a lightweight dashboard over the reporting outputs
