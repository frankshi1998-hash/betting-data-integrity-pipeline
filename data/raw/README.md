# Raw Data Format

The real source data is currently delivered as Excel workbooks, not CSV files.

## Current Source Shape

- file type: `.xlsx`
- one worksheet per workbook
- shared 52-column export structure
- monthly bookmaker dump format

## What This Means For The Pipeline

For the raw layer, we should not force these files into a normalized betting schema immediately.

Instead, we should:

1. read the Excel rows as source records
2. preserve the original columns in a raw landing table
3. normalize the data in a later staging step

## Why We Preserve The Source First

The dump contains values like:

- currency strings such as `$1,000.00`
- negative values such as `($10.00)`
- separate date and time columns
- mixed boolean and flag fields
- source-specific columns such as `BetBack Flag` and `Horse Win Hold`

If we try to force this directly into a clean transaction model too early, we make ingestion fragile and lose source fidelity.

## Next Transformation Goal

After landing the dump into the raw table, the staging model derives cleaner fields such as:

- `bet_id`
- `client_reference`
- `event_name`
- `bet_timestamp`
- `stake_amount`
- `payout_amount`
- `is_cancelled`
- `is_paid`

For public demos, the project can generate a synthetic workbook with the same header contract:

```powershell
python -m src.data_generation.create_demo_workbook
```
