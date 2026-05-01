# Source Profile

## Files Found

The current raw source folder contains 5 Excel workbooks:

- `dump 01032026 - 31032026 (COT).xlsx`
- `dump 01032026 - 31032026 (JOT).xlsx`
- `dump 01032026 - 31032026 (LOT).xlsx`
- `dump 01032026 - 31032026 (POT).xlsx`
- `dump 01032026 - 31032026 (XOT).xlsx`

## Structural Profile

Each workbook currently has:

- 1 worksheet
- 52 columns
- the same header structure across files

Observed row counts:

- `COT`: 19,203 data rows
- `JOT`: 69,783 data rows
- `LOT`: 7,733 data rows
- `POT`: 34,244 data rows
- `XOT`: 4,637 data rows

## Important Design Decision

The raw layer should mirror the source closely.

Why:

- the dumps contain mixed types
- numeric values are often stored like `$1,000.00`
- some negative values use parentheses like `($10.00)`
- booleans and flags are inconsistent across fields
- dates and times are split into separate columns

Because of that, the raw landing table should preserve most source columns as text first.

Then a later staging step can:

- parse currency strings
- combine date and time fields
- standardize boolean flags
- derive normalized bet and settlement records

## Shared Source Headers

The shared workbook headers are:

- `REFID`
- `UUID`
- `License`
- `Bookmaker`
- `Location`
- `State`
- `Area`
- `Wagering Provider`
- `SysVerNo`
- `Bet Date`
- `Bet Time`
- `Event Date`
- `Event Time`
- `Ticket No`
- `Event`
- `Sport Event`
- `Venue`
- `Venue State`
- `Bet Type`
- `Bet Method`
- `Bet Details`
- `Race Number`
- `Runner Number`
- `Runner Name`
- `Bet Amount Win`
- `Bet Amount Place`
- `WinPrice`
- `Place Price`
- `Customer Name`
- `Betback Claim`
- `Bet Information`
- `Cancelled Flag`
- `Time Cancelled`
- `Bet Win Takeout`
- `Bet Place Takeout`
- `Horse Win Takeout`
- `Horse Win Hold`
- `Horse Place Takeout`
- `Horse PlaceHold`
- `Race Hold`
- `BetBack Information`
- `BetBack Flag`
- `Refund Flag`
- `Placing`
- `Win Deduction`
- `Place Deduction`
- `Win Result`
- `Place Result`
- `Win Payout Amount`
- `Place Payout Amount`
- `Paid Status`
- `Bet Terminal`
