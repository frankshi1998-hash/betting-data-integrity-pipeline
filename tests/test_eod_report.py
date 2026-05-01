import sys
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.generate_eod_report import render_markdown_report, render_table


class EodReportTests(unittest.TestCase):
    def test_render_table_handles_empty_rows(self) -> None:
        self.assertEqual(render_table(["a", "b"], []), "_No rows found._")

    def test_render_markdown_report_includes_operational_sections(self) -> None:
        report = render_markdown_report(
            generated_at=datetime(2026, 3, 1, 18, 30),
            overview={
                "source_day_count": 1,
                "total_bet_rows": 600,
                "review_source_day_count": 1,
                "high_risk_source_day_count": 1,
                "total_alert_count": 3,
                "total_quality_issue_count": 341,
                "max_anomaly_score": Decimal("95.25"),
                "total_stake_amount": Decimal("60088.00"),
                "total_payout_amount": Decimal("94670.40"),
                "net_revenue_amount": Decimal("-34582.40"),
            },
            risk_bands=[
                {
                    "risk_band": "critical",
                    "source_day_count": 1,
                    "max_anomaly_score": Decimal("95.25"),
                }
            ],
            top_anomalies=[
                {
                    "report_date": "2026-03-01",
                    "source_file": "demo_bookmaker_bet_dump.xlsx",
                    "anomaly_score": Decimal("95.25"),
                    "risk_band": "critical",
                    "primary_driver": "duplicate_pressure",
                    "recommended_action": "Immediate integrity and finance review",
                    "total_bet_rows": 600,
                    "total_issue_rows": 341,
                    "alert_count": 3,
                    "payout_ratio": Decimal("1.5755"),
                }
            ],
            alert_summary=[
                {"severity": "critical", "alert_type": "loss_day_payout_ratio", "alert_count": 1}
            ],
            quality_issues=[
                {"issue_type": "duplicate_bet_key", "issue_count": 242}
            ],
        )

        self.assertIn("# EOD Betting Integrity Report", report)
        self.assertIn("## Executive Summary", report)
        self.assertIn("## Top Anomaly Priorities", report)
        self.assertIn("Immediate integrity and finance review", report)
        self.assertIn("duplicate_bet_key", report)


if __name__ == "__main__":
    unittest.main()
