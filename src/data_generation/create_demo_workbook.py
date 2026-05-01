from __future__ import annotations

import argparse
from pathlib import Path

from openpyxl import Workbook

from src.config import RAW_DATA_DIR
from src.ingest.load_bookmaker_dump import HEADER_TO_COLUMN

HEADERS = list(HEADER_TO_COLUMN.keys())
DEFAULT_OUTPUT_PATH = RAW_DATA_DIR / "demo_bookmaker_bet_dump.xlsx"
DEFAULT_ROW_COUNT = 600


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a small synthetic bookmaker Excel dump for local demos."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Workbook path to write.",
    )
    parser.add_argument(
        "--row-count",
        type=int,
        default=DEFAULT_ROW_COUNT,
        help="Number of synthetic rows to create. Use at least 600 to trigger all demo alert thresholds.",
    )
    return parser.parse_args()


def make_row(**overrides: str | None) -> dict[str, str | None]:
    row = {header: None for header in HEADERS}
    row.update(
        {
            "License": "DEMO-LIC",
            "Bookmaker": "Demo Bookmaker",
            "Location": "Demo Venue",
            "State": "NSW",
            "Area": "Metro",
            "Wagering Provider": "DemoWager",
            "SysVerNo": "1.0",
            "Bet Date": "2026-03-01",
            "Bet Time": "12:00:00",
            "Event Date": "2026-03-01",
            "Event Time": "15:00:00",
            "Event": "RACING",
            "Sport Event": "Demo Race Day",
            "Venue": "Sample Park",
            "Venue State": "NSW",
            "Bet Type": "WIN",
            "Bet Method": "Terminal",
            "Race Number": "1",
            "Runner Number": "4",
            "Runner Name": "Example Runner",
            "Bet Amount Win": "$10.00",
            "Bet Amount Place": "$0.00",
            "WinPrice": "3.20",
            "Place Price": "1.40",
            "Customer Name": "Demo Customer",
            "Cancelled Flag": "N",
            "BetBack Flag": "N",
            "Refund Flag": "N",
            "Win Payout Amount": "$0.00",
            "Place Payout Amount": "$0.00",
            "Paid Status": "Unpaid",
            "Bet Terminal": "TERM-01",
        }
    )
    row.update(overrides)
    return row


def build_edge_case_rows() -> list[dict[str, str | None]]:
    return [
        make_row(
            REFID="DEMO_0001",
            UUID="demo-uuid-0001",
            **{"Ticket No": "TKT-0001", "Win Payout Amount": "$32.00", "Paid Status": "Paid"},
        ),
        make_row(
            REFID="DEMO_0002",
            UUID="demo-uuid-duplicate",
            **{"Ticket No": "TKT-DUP-001", "Bet Amount Win": "$15.00"},
        ),
        make_row(
            REFID="DEMO_0003",
            UUID="demo-uuid-duplicate",
            **{"Ticket No": "TKT-DUP-001", "Bet Amount Win": "$15.00"},
        ),
        make_row(
            REFID="DEMO_0004",
            UUID="demo-uuid-negative-stake",
            **{"Ticket No": "TKT-0004", "Bet Amount Win": "($20.00)"},
        ),
        make_row(
            REFID="DEMO_0005",
            UUID="demo-uuid-missing-event",
            **{"Ticket No": "TKT-0005", "Event Date": None, "Event Time": None},
        ),
        make_row(
            REFID="DEMO_0006",
            UUID="demo-uuid-cancelled-payout",
            **{
                "Ticket No": "TKT-0006",
                "Cancelled Flag": "Y",
                "Time Cancelled": "12:05:00",
                "Win Payout Amount": "$25.00",
                "Paid Status": "Paid",
            },
        ),
        make_row(
            REFID="DEMO_0007",
            UUID="demo-uuid-payout-no-stake",
            **{
                "Ticket No": "TKT-0007",
                "Bet Amount Win": "$0.00",
                "Bet Amount Place": "$0.00",
                "Win Payout Amount": "$50.00",
                "Paid Status": "Paid",
            },
        ),
        make_row(
            REFID="DEMO_0008",
            UUID="demo-uuid-place-bet",
            **{
                "Ticket No": "TKT-0008",
                "Bet Type": "PLACE",
                "Bet Amount Win": "$0.00",
                "Bet Amount Place": "$8.00",
                "Place Payout Amount": "$18.40",
                "Paid Status": "Paid",
            },
        ),
    ]


def build_operational_rows(row_count: int = DEFAULT_ROW_COUNT) -> list[dict[str, str | None]]:
    if row_count < 8:
        raise ValueError("row_count must be at least 8")

    rows = build_edge_case_rows()

    for index in range(len(rows) + 1, row_count + 1):
        duplicate_pair = index <= 248
        duplicate_group = (index - 9) // 2 if duplicate_pair else index
        is_negative_stake = 249 <= index <= 328
        is_cancelled_with_payout = index in {329, 330, 331, 332, 333}
        is_missing_event_timestamp = index in {334, 335, 336, 337, 338}
        is_payout_without_stake = index in {339, 340, 341, 342, 343}

        stake_amount = "($10.00)" if is_negative_stake else "$120.00"
        payout_amount = "$160.00"
        ticket_no = f"TKT-DUP-{duplicate_group:04d}" if duplicate_pair else f"TKT-{index:04d}"
        source_uuid = f"demo-uuid-dup-{duplicate_group:04d}" if duplicate_pair else f"demo-uuid-{index:04d}"

        overrides: dict[str, str | None] = {
            "REFID": f"DEMO_{index:04d}",
            "UUID": source_uuid,
            "Ticket No": ticket_no,
            "Bet Time": f"12:{index % 60:02d}:00",
            "Runner Number": str((index % 12) + 1),
            "Runner Name": f"Example Runner {(index % 12) + 1}",
            "Bet Amount Win": stake_amount,
            "Win Payout Amount": payout_amount,
            "Paid Status": "Paid",
        }

        if is_cancelled_with_payout:
            overrides["Cancelled Flag"] = "Y"
            overrides["Time Cancelled"] = f"13:{index % 60:02d}:00"

        if is_missing_event_timestamp:
            overrides["Event Date"] = None
            overrides["Event Time"] = None

        if is_payout_without_stake:
            overrides["Bet Amount Win"] = "$0.00"
            overrides["Bet Amount Place"] = "$0.00"
            overrides["Win Payout Amount"] = "$125.00"

        rows.append(make_row(**overrides))

    return rows


def build_demo_rows(row_count: int = DEFAULT_ROW_COUNT) -> list[dict[str, str | None]]:
    return build_operational_rows(row_count=row_count)


def write_workbook(output_path: Path, rows: list[dict[str, str | None]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "demo_bookmaker_bet_dump"
    worksheet.append(HEADERS)

    for row in rows:
        worksheet.append([row.get(header) for header in HEADERS])

    workbook.save(output_path)


def main() -> None:
    args = parse_args()
    rows = build_demo_rows(row_count=args.row_count)
    write_workbook(args.output_path, rows)
    print(f"Wrote {len(rows)} demo rows to {args.output_path}")


if __name__ == "__main__":
    main()
