import sys
import unittest
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_generation.create_demo_workbook import HEADERS, build_demo_rows
from src.ingest.load_bookmaker_dump import HEADER_TO_COLUMN, validate_headers


class DemoWorkbookGeneratorTests(unittest.TestCase):
    def test_demo_headers_match_loader_contract(self) -> None:
        self.assertEqual(HEADERS, list(HEADER_TO_COLUMN.keys()))
        validate_headers(HEADERS)

    def test_demo_rows_include_quality_scenarios(self) -> None:
        rows = build_demo_rows()
        duplicate_keys = Counter((row["UUID"], row["Ticket No"]) for row in rows)

        self.assertGreaterEqual(len(rows), 600)
        self.assertTrue(any(count > 1 for count in duplicate_keys.values()))
        self.assertTrue(any(row["Bet Amount Win"] == "($20.00)" for row in rows))
        self.assertTrue(any(row["Event Date"] is None for row in rows))
        self.assertTrue(
            any(row["Cancelled Flag"] == "Y" and row["Win Payout Amount"] == "$25.00" for row in rows)
        )
        self.assertTrue(
            any(row["Bet Amount Win"] == "$0.00" and row["Win Payout Amount"] == "$50.00" for row in rows)
        )

    def test_demo_rows_can_trigger_operational_alert_thresholds(self) -> None:
        rows = build_demo_rows()
        duplicate_extra_rows = sum(
            count - 1
            for count in Counter((row["UUID"], row["Ticket No"]) for row in rows).values()
            if count > 1
        )
        negative_stake_rows = sum(1 for row in rows if row["Bet Amount Win"] in {"($10.00)", "($20.00)"})
        total_positive_stake = sum(
            120
            for row in rows
            if row["Bet Amount Win"] == "$120.00"
        )

        self.assertGreaterEqual(len(rows), 500)
        self.assertGreaterEqual(duplicate_extra_rows, 100)
        self.assertGreaterEqual(negative_stake_rows, 50)
        self.assertGreaterEqual(total_positive_stake, 50_000)


if __name__ == "__main__":
    unittest.main()
