import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reporting.generate_lineage import (
    LINEAGE_MANIFEST_FILENAME,
    LINEAGE_REPORT_FILENAME,
    build_lineage_manifest,
    render_markdown_report,
    write_lineage_artifacts,
)


class LineageTests(unittest.TestCase):
    def test_build_lineage_manifest_includes_sources_stages_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "raw"
            output_dir = root / "processed"
            raw_dir.mkdir()
            output_dir.mkdir()
            (raw_dir / "demo_bookmaker_bet_dump.xlsx").write_text("placeholder", encoding="utf-8")
            (output_dir / "anomaly_scorecard.csv").write_text("x", encoding="utf-8")
            (output_dir / "integrity_dashboard.html").write_text("<html></html>", encoding="utf-8")

            manifest = build_lineage_manifest(
                raw_dir=raw_dir,
                output_dir=output_dir,
                generated_at=datetime(2026, 3, 1, 18, 0),
            )

        self.assertEqual(manifest["pipeline_name"], "betting-data-integrity-pipeline")
        self.assertEqual(manifest["source_files"], ["demo_bookmaker_bet_dump.xlsx"])
        self.assertGreaterEqual(len(manifest["stages"]), 8)
        self.assertEqual(len(manifest["artifact_inventory"]), 2)
        self.assertTrue(
            any(stage["stage_id"] == "raw_ingestion" for stage in manifest["stages"])
        )

    def test_render_markdown_report_includes_mermaid_and_artifact_inventory(self) -> None:
        manifest = {
            "generated_at": "2026-03-01T18:00:00",
            "pipeline_name": "betting-data-integrity-pipeline",
            "lineage_version": "1.0",
            "raw_dir": "raw",
            "output_dir": "processed",
            "source_files": ["demo.xlsx"],
            "stages": [
                {
                    "stage_id": "raw_ingestion",
                    "name": "Raw PostgreSQL ingestion",
                    "layer": "raw",
                    "description": "Load raw data.",
                    "inputs": ["demo.xlsx"],
                    "outputs": ["raw.bookmaker_bet_dump"],
                    "code_assets": ["src.ingest.load_bookmaker_dump"],
                    "quality_controls": ["Header validation"],
                }
            ],
            "artifact_inventory": [
                {
                    "name": "anomaly_scorecard.csv",
                    "path": "processed/anomaly_scorecard.csv",
                    "size_bytes": 10,
                }
            ],
            "artifact_lineage": [
                {
                    "artifact": "anomaly_scorecard.csv",
                    "path": "processed/anomaly_scorecard.csv",
                    "size_bytes": 10,
                    "purpose": "Explainable source-day anomaly ranking.",
                }
            ],
        }

        report = render_markdown_report(manifest)

        self.assertIn("# Data Lineage Report", report)
        self.assertIn("```mermaid", report)
        self.assertIn("Raw PostgreSQL ingestion", report)
        self.assertIn("anomaly_scorecard.csv", report)

    def test_write_lineage_artifacts_creates_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_dir = root / "raw"
            output_dir = root / "processed"
            raw_dir.mkdir()
            output_dir.mkdir()
            (raw_dir / "demo.xlsx").write_text("placeholder", encoding="utf-8")
            (output_dir / "alert_feed.csv").write_text("x", encoding="utf-8")

            manifest_path, report_path = write_lineage_artifacts(raw_dir, output_dir)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            report_text = report_path.read_text(encoding="utf-8")

        self.assertEqual(manifest_path.name, LINEAGE_MANIFEST_FILENAME)
        self.assertEqual(report_path.name, LINEAGE_REPORT_FILENAME)
        self.assertEqual(manifest["source_files"], ["demo.xlsx"])
        self.assertIn("Data Lineage Report", report_text)


if __name__ == "__main__":
    unittest.main()
