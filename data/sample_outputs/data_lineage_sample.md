# Data Lineage Report

Generated at: `2026-05-02T00:00:00`

## Run Scope

- Pipeline: `betting-data-integrity-pipeline`
- Lineage version: `1.0`
- Raw directory: `ci_artifacts/demo_raw`
- Output directory: `ci_artifacts/demo_processed`
- Source files: `1`
- Generated artifacts inventoried: `1`

## Source Files

- `demo_bookmaker_bet_dump.xlsx`

## Lineage Flow

```mermaid
flowchart LR
  A["Excel workbooks"] --> B["raw.bookmaker_bet_dump"]
  B --> C["stage.bookmaker_bets_clean"]
  C --> D["core models"]
  D --> E["quality checks"]
  E --> F["reporting views"]
  F --> G["CSV / Markdown outputs"]
  F --> H["ML anomaly scoring"]
  G --> I["HTML dashboard"]
  H --> I
  I --> J["lineage + run summary artifacts"]
```

## Processing Stages

### Raw PostgreSQL ingestion

- Stage ID: `raw_ingestion`
- Layer: `raw`
- Description: Workbook rows are loaded with source file, source row number, source UUID, and ingestion metadata.

## Artifact Inventory

| artifact | size_bytes | purpose |
| --- | ---: | --- |
| `integrity_dashboard.html` | 10968 | Static portfolio dashboard for browser-based review. |
