import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.generate_dashboard import (
    DASHBOARD_FILENAME,
    build_context,
    generate_dashboard,
    render_dashboard_html,
)


def write_artifact(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class DashboardTests(unittest.TestCase):
    def test_build_context_summarizes_reporting_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            write_artifact(
                output_dir / "daily_reconciliation_summary.csv",
                "\n".join(
                    [
                        "source_file,report_date,total_bet_rows,total_stake_amount,total_payout_amount,net_revenue_amount,reconciliation_status",
                        "demo_bookmaker_bet_dump.xlsx,2026-03-01,600,60088.00,94670.40,-34582.40,review",
                    ]
                )
                + "\n",
            )
            write_artifact(
                output_dir / "anomaly_scorecard.csv",
                "\n".join(
                    [
                        "source_file,report_date,anomaly_score,risk_band,primary_driver,recommended_action",
                        "demo_bookmaker_bet_dump.xlsx,2026-03-01,95.25,critical,duplicate_pressure,Immediate integrity and finance review",
                    ]
                )
                + "\n",
            )
            write_artifact(
                output_dir / "alert_feed.csv",
                "\n".join(
                    [
                        "severity,alert_type",
                        "critical,loss_day_payout_ratio",
                        "high,duplicate_ratio_spike",
                    ]
                )
                + "\n",
            )
            write_artifact(
                output_dir / "daily_issue_summary.csv",
                "\n".join(
                    [
                        "issue_type,issue_count",
                        "duplicate_bet_key,242",
                        "negative_stake,81",
                    ]
                )
                + "\n",
            )
            write_artifact(
                output_dir / "ml_anomaly_scores.csv",
                "\n".join(
                    [
                        "source_file,report_date,ml_anomaly_score,ml_risk_band,model_outlier_flag,model_driver",
                        "demo_bookmaker_bet_dump.xlsx,2026-03-01,100.0,critical,True,net revenue movement",
                    ]
                )
                + "\n",
            )

            context = build_context(output_dir, generated_at=datetime(2026, 3, 1, 18, 0))

        self.assertEqual(context.source_day_count, 1)
        self.assertEqual(context.total_bet_rows, 600)
        self.assertEqual(context.review_source_day_count, 1)
        self.assertEqual(context.high_risk_source_day_count, 1)
        self.assertEqual(context.alert_count, 2)
        self.assertEqual(context.ml_outlier_count, 1)
        self.assertEqual(context.max_rule_score, 95.25)
        self.assertEqual(context.max_ml_score, 100.0)

    def test_render_dashboard_html_includes_operational_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            write_artifact(
                output_dir / "daily_reconciliation_summary.csv",
                "source_file,report_date,total_bet_rows,total_stake_amount,total_payout_amount,net_revenue_amount,reconciliation_status\n"
                "demo_bookmaker_bet_dump.xlsx,2026-03-01,600,60088.00,94670.40,-34582.40,review\n",
            )
            write_artifact(
                output_dir / "anomaly_scorecard.csv",
                "source_file,report_date,anomaly_score,risk_band,primary_driver,recommended_action\n"
                "demo_bookmaker_bet_dump.xlsx,2026-03-01,95.25,critical,duplicate_pressure,Immediate integrity and finance review\n",
            )
            write_artifact(output_dir / "alert_feed.csv", "severity,alert_type\ncritical,loss_day_payout_ratio\n")
            write_artifact(output_dir / "daily_issue_summary.csv", "issue_type,issue_count\nduplicate_bet_key,242\n")
            write_artifact(
                output_dir / "ml_anomaly_scores.csv",
                "source_file,report_date,ml_anomaly_score,ml_risk_band,model_outlier_flag,model_driver\n"
                "demo_bookmaker_bet_dump.xlsx,2026-03-01,100.0,critical,True,net revenue movement\n",
            )

            html = render_dashboard_html(build_context(output_dir))

        self.assertIn("Operational risk, reconciled.", html)
        self.assertIn("Rule-Based Anomaly Priorities", html)
        self.assertIn("ML Outlier Priorities", html)
        self.assertIn("duplicate_pressure", html)
        self.assertIn("net revenue movement", html)

    def test_generate_dashboard_writes_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            write_artifact(output_dir / "daily_reconciliation_summary.csv", "source_file,report_date,total_bet_rows,total_stake_amount,total_payout_amount,net_revenue_amount,reconciliation_status\n")
            write_artifact(output_dir / "anomaly_scorecard.csv", "source_file,report_date,anomaly_score,risk_band,primary_driver,recommended_action\n")
            write_artifact(output_dir / "alert_feed.csv", "severity,alert_type\n")
            write_artifact(output_dir / "daily_issue_summary.csv", "issue_type,issue_count\n")
            write_artifact(output_dir / "ml_anomaly_scores.csv", "source_file,report_date,ml_anomaly_score,ml_risk_band,model_outlier_flag,model_driver\n")

            dashboard_path = generate_dashboard(output_dir)
            dashboard_size = dashboard_path.stat().st_size

        self.assertEqual(dashboard_path.name, DASHBOARD_FILENAME)
        self.assertGreater(dashboard_size, 0)


if __name__ == "__main__":
    unittest.main()
