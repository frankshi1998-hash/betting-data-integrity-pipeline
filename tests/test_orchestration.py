import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.orchestration.run_pipeline import (
    EXPECTED_ALERT_TYPES,
    EXPECTED_ARTIFACTS,
    ArtifactSummary,
    PipelineConfig,
    PipelineMetrics,
    QualityGateError,
    build_dbt_commands,
    build_python_module_command,
    build_run_summary,
    collect_artifact_summaries,
    parse_args,
    validate_quality_gates,
)


class OrchestrationTests(unittest.TestCase):
    def test_parse_args_defaults(self) -> None:
        args = parse_args([])

        self.assertFalse(args.demo)
        self.assertEqual(args.raw_dir, RAW_DATA_DIR)
        self.assertFalse(args.replace_files)
        self.assertFalse(args.skip_dbt)
        self.assertFalse(args.require_demo_alerts)

    def test_build_python_module_command_uses_current_interpreter(self) -> None:
        command = build_python_module_command("src.setup.apply_sql_pipeline", "--stop-after", "x.sql")

        self.assertEqual(command[:3], [sys.executable, "-m", "src.setup.apply_sql_pipeline"])
        self.assertEqual(command[-2:], ["--stop-after", "x.sql"])

    def test_build_dbt_commands_can_be_skipped(self) -> None:
        self.assertEqual(build_dbt_commands(skip_dbt=True), [])

    def test_build_dbt_commands_include_expected_steps(self) -> None:
        commands = build_dbt_commands(skip_dbt=False)

        self.assertEqual([command[1] for command in commands], ["debug", "parse", "run", "test"])
        self.assertTrue(all("--project-dir" in command for command in commands))
        self.assertTrue(all("--profiles-dir" in command for command in commands))

    def test_collect_artifact_summaries_requires_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            for filename in EXPECTED_ARTIFACTS:
                (output_dir / filename).write_text("x", encoding="utf-8")

            summaries = collect_artifact_summaries(output_dir)

        self.assertEqual(len(summaries), len(EXPECTED_ARTIFACTS))
        self.assertTrue(all(summary.size_bytes > 0 for summary in summaries))

    def test_quality_gates_pass_for_expected_demo_metrics(self) -> None:
        source_files = ["demo_bookmaker_bet_dump.xlsx"]
        artifacts = [
            ArtifactSummary(name=filename, path=f"out/{filename}", size_bytes=10)
            for filename in EXPECTED_ARTIFACTS
        ]
        metrics = PipelineMetrics(
            source_row_counts={"demo_bookmaker_bet_dump.xlsx": 600},
            anomaly_row_count=1,
            max_anomaly_score=95.25,
            critical_anomaly_count=1,
            alert_types=sorted(EXPECTED_ALERT_TYPES),
        )

        result = validate_quality_gates(
            source_files=source_files,
            artifacts=artifacts,
            metrics=metrics,
            require_demo_alerts=True,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["source_file_count"], 1)

    def test_quality_gates_fail_when_demo_alert_is_missing(self) -> None:
        source_files = ["demo_bookmaker_bet_dump.xlsx"]
        artifacts = [
            ArtifactSummary(name=filename, path=f"out/{filename}", size_bytes=10)
            for filename in EXPECTED_ARTIFACTS
        ]
        metrics = PipelineMetrics(
            source_row_counts={"demo_bookmaker_bet_dump.xlsx": 600},
            anomaly_row_count=1,
            max_anomaly_score=70.0,
            critical_anomaly_count=0,
            alert_types=["duplicate_ratio_spike"],
        )

        with self.assertRaises(QualityGateError):
            validate_quality_gates(
                source_files=source_files,
                artifacts=artifacts,
                metrics=metrics,
                require_demo_alerts=True,
            )

    def test_build_run_summary_shape(self) -> None:
        config = PipelineConfig(
            demo=True,
            raw_dir=Path("raw"),
            output_dir=Path("out"),
            replace_files=True,
            skip_dbt=True,
            require_demo_alerts=True,
        )
        artifacts = [ArtifactSummary(name="x.csv", path="out/x.csv", size_bytes=10)]
        metrics = PipelineMetrics(
            source_row_counts={"demo.xlsx": 1},
            anomaly_row_count=1,
            max_anomaly_score=95.25,
            critical_anomaly_count=1,
            alert_types=["duplicate_ratio_spike"],
        )

        summary = build_run_summary(
            config=config,
            source_files=["demo.xlsx"],
            artifacts=artifacts,
            metrics=metrics,
            quality_gates={"passed": True},
            dbt_skipped=True,
        )

        self.assertIn("run_id", summary)
        self.assertEqual(summary["config"]["raw_dir"], "raw")
        self.assertEqual(summary["source_files"], ["demo.xlsx"])
        self.assertEqual(summary["artifacts"][0]["name"], "x.csv")
        self.assertTrue(summary["quality_gates"]["passed"])
        self.assertTrue(summary["dbt"]["skipped"])


if __name__ == "__main__":
    unittest.main()
