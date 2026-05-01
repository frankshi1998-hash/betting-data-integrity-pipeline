import sys
import unittest
from datetime import datetime, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.load_bookmaker_dump import (
    build_record,
    normalize_headers,
    preview_record,
    stringify_cell,
    validate_headers,
)


class BookmakerDumpLoaderTests(unittest.TestCase):
    def test_stringify_cell_handles_supported_types(self) -> None:
        self.assertIsNone(stringify_cell(None))
        self.assertEqual(stringify_cell(True), "true")
        self.assertEqual(stringify_cell(False), "false")
        self.assertEqual(
            stringify_cell(datetime(2026, 3, 1, 12, 30, 29)),
            "2026-03-01T12:30:29",
        )
        self.assertEqual(stringify_cell(time(12, 30, 29)), "12:30:29")
        self.assertEqual(stringify_cell("  $1,000.00  "), "$1,000.00")
        self.assertEqual(stringify_cell("$1,000.00"), "$1,000.00")

    def test_validate_headers_rejects_unknown_source_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown source headers"):
            validate_headers(["REFID", "Unexpected Column"])

    def test_build_record_maps_source_headers_to_database_columns(self) -> None:
        headers = normalize_headers(["REFID", "UUID", "Bet Date", "Bet Time", "Bet Amount Win"])
        values = ("SALE_01032026_1", "abc-123", datetime(2026, 3, 1), time(12, 4, 5), "$5.00")

        record, raw_payload = build_record(headers, values)

        self.assertEqual(record["refid"], "SALE_01032026_1")
        self.assertEqual(record["source_uuid"], "abc-123")
        self.assertEqual(record["bet_date"], "2026-03-01T00:00:00")
        self.assertEqual(record["bet_time"], "12:04:05")
        self.assertEqual(record["bet_amount_win"], "$5.00")
        self.assertEqual(raw_payload["REFID"], "SALE_01032026_1")

    def test_preview_record_keeps_useful_sample_fields(self) -> None:
        record = {
            "refid": "SALE_01032026_1",
            "bookmaker": "COT",
            "bet_date": "2026-03-01T00:00:00",
            "bet_time": "12:04:05",
            "sport_event": "Sydney FC v Victory",
            "bet_type": "Win",
            "bet_amount_win": "$5.00",
            "customer_name": "Jane Smith",
        }

        preview = preview_record(record)

        self.assertIn('"refid": "SALE_01032026_1"', preview)
        self.assertIn('"bookmaker": "COT"', preview)
        self.assertIn('"customer_name": "Jane Smith"', preview)


if __name__ == "__main__":
    unittest.main()
