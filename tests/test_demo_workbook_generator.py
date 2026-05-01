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

        self.assertTrue(any(count > 1 for count in duplicate_keys.values()))
        self.assertTrue(any(row["Bet Amount Win"] == "($20.00)" for row in rows))
        self.assertTrue(any(row["Event Date"] is None for row in rows))
        self.assertTrue(
            any(row["Cancelled Flag"] == "Y" and row["Win Payout Amount"] == "$25.00" for row in rows)
        )
        self.assertTrue(
            any(row["Bet Amount Win"] == "$0.00" and row["Win Payout Amount"] == "$50.00" for row in rows)
        )


if __name__ == "__main__":
    unittest.main()
