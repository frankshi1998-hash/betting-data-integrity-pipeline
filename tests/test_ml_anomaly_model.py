import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anomaly_detection.ml_anomaly_model import (
    ML_REPORT_FILENAME,
    ML_SCORE_FILENAME,
    OUTPUT_COLUMNS,
    render_markdown_report,
    score_rows,
    write_report,
    write_scores_csv,
)


def build_scorecard_row(index: int, *, extreme: bool = False) -> dict[str, object]:
    if extreme:
        return {
            "anomaly_id": f"critical-{index}",
            "source_file": "demo_bookmaker_bet_dump.xlsx",
            "report_date": "2026-03-31",
            "anomaly_score": 95.25,
            "risk_band": "critical",
            "primary_driver": "duplicate_pressure",
            "recommended_action": "Immediate integrity and finance review",
            "total_bet_rows": 600,
            "total_issue_rows": 341,
            "duplicate_ratio": 0.4033,
            "negative_stake_ratio": 0.1017,
            "issue_ratio": 0.5683,
            "payout_ratio": 1.5755,
            "alert_count": 3,
            "critical_alert_count": 1,
            "net_revenue_amount": -34582.40,
        }

    return {
        "anomaly_id": f"normal-{index}",
        "source_file": f"normal_{index:02d}.xlsx",
        "report_date": f"2026-03-{index + 1:02d}",
        "anomaly_score": 2.0 + (index % 3),
        "risk_band": "normal",
        "primary_driver": "none",
        "recommended_action": "No action required",
        "total_bet_rows": 100 + index,
        "total_issue_rows": index % 2,
        "duplicate_ratio": 0.0,
        "negative_stake_ratio": 0.0,
        "issue_ratio": 0.01,
        "payout_ratio": 0.72,
        "alert_count": 0,
        "critical_alert_count": 0,
        "net_revenue_amount": 1800.00 + index,
    }


class MlAnomalyModelTests(unittest.TestCase):
    def test_score_rows_flags_extreme_source_day(self) -> None:
        rows = [build_scorecard_row(index) for index in range(20)]
        rows.append(build_scorecard_row(99, extreme=True))

        scored_rows = score_rows(rows)
        top_row = scored_rows[0]

        self.assertEqual(len(scored_rows), 21)
        self.assertEqual(top_row["source_file"], "demo_bookmaker_bet_dump.xlsx")
        self.assertTrue(top_row["model_outlier_flag"])
        self.assertEqual(top_row["ml_risk_band"], "critical")
        self.assertTrue(all(0 <= row["ml_anomaly_score"] <= 100 for row in scored_rows))

    def test_score_rows_handles_small_batches(self) -> None:
        scored_rows = score_rows([build_scorecard_row(99, extreme=True)])

        self.assertEqual(len(scored_rows), 1)
        self.assertEqual(scored_rows[0]["ml_anomaly_score"], 95.25)
        self.assertTrue(scored_rows[0]["model_outlier_flag"])

    def test_render_markdown_report_includes_model_context(self) -> None:
        scored_rows = score_rows([build_scorecard_row(index) for index in range(5)])

        report = render_markdown_report(scored_rows, datetime(2026, 3, 31, 18, 0))

        self.assertIn("# ML Anomaly Model Report", report)
        self.assertIn("Isolation Forest", report)
        self.assertIn("Rows scored", report)
        self.assertIn("Top ML Anomaly Priorities", report)

    def test_writers_create_non_empty_artifacts(self) -> None:
        scored_rows = score_rows([build_scorecard_row(index) for index in range(5)])

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            scores_path = output_dir / ML_SCORE_FILENAME
            report_path = output_dir / ML_REPORT_FILENAME
            write_scores_csv(scored_rows, scores_path)
            write_report(scored_rows, report_path)

            score_header = scores_path.read_text(encoding="utf-8").splitlines()[0].split(",")
            scores_size = scores_path.stat().st_size
            report_size = report_path.stat().st_size

        self.assertEqual(score_header, OUTPUT_COLUMNS)
        self.assertGreater(scores_size, 0)
        self.assertGreater(report_size, 0)


if __name__ == "__main__":
    unittest.main()
