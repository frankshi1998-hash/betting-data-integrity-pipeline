from __future__ import annotations

import argparse
from pathlib import Path

from openpyxl import Workbook

from src.config import RAW_DATA_DIR
from src.ingest.load_bookmaker_dump import HEADER_TO_COLUMN

HEADERS = list(HEADER_TO_COLUMN.keys())
DEFAULT_OUTPUT_PATH = RAW_DATA_DIR / "demo_bookmaker_bet_dump.xlsx"


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


def build_demo_rows() -> list[dict[str, str | None]]:
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
    rows = build_demo_rows()
    write_workbook(args.output_path, rows)
    print(f"Wrote {len(rows)} demo rows to {args.output_path}")


if __name__ == "__main__":
    main()
