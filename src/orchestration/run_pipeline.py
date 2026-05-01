from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg

# Local demo/CI runs should be deterministic and quiet; Prefect's optional
# analytics service can contend for the temporary SQLite server database.
os.environ.setdefault("PREFECT_SERVER_ANALYTICS_ENABLED", "false")
os.environ.setdefault("DO_NOT_TRACK", "1")

from prefect import flow, task

from src.config import PROJECT_ROOT, RAW_DATA_DIR, get_database_config

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
DEMO_WORKBOOK_NAME = "demo_bookmaker_bet_dump.xlsx"
EXPECTED_ALERT_TYPES = {
    "duplicate_ratio_spike",
    "negative_stake_spike",
    "loss_day_payout_ratio",
}
EXPECTED_ARTIFACTS = [
    "daily_reconciliation_summary.csv",
    "daily_issue_summary.csv",
    "daily_bookmaker_summary.csv",
    "alert_feed.csv",
    "alert_summary.csv",
    "anomaly_scorecard.csv",
    "eod_integrity_report.md",
]


class QualityGateError(RuntimeError):
    """Raised when post-pipeline validation fails."""


@dataclass(frozen=True)
class PipelineConfig:
    demo: bool
    raw_dir: Path
    output_dir: Path
    replace_files: bool
    skip_dbt: bool
    require_demo_alerts: bool


@dataclass(frozen=True)
class ArtifactSummary:
    name: str
    path: str
    size_bytes: int


@dataclass(frozen=True)
class PipelineMetrics:
    source_row_counts: dict[str, int]
    anomaly_row_count: int
    max_anomaly_score: float
    critical_anomaly_count: int
    alert_types: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the betting data integrity pipeline as an orchestrated workflow."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate a synthetic demo workbook before loading data.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing source .xlsx files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where reporting artifacts are written.",
    )
    parser.add_argument(
        "--replace-files",
        action="store_true",
        help="Delete existing raw rows for loaded source files before reloading.",
    )
    parser.add_argument(
        "--skip-dbt",
        action="store_true",
        help="Skip dbt debug, parse, run, and test for a faster local workflow.",
    )
    parser.add_argument(
        "--require-demo-alerts",
        action="store_true",
        help="Fail unless demo data produces expected alerts and a critical anomaly.",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        demo=args.demo,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        replace_files=args.replace_files,
        skip_dbt=args.skip_dbt,
        require_demo_alerts=args.require_demo_alerts,
    )


def build_python_module_command(module: str, *module_args: str) -> list[str]:
    return [sys.executable, "-m", module, *module_args]


def resolve_dbt_command() -> str:
    executable_name = "dbt.exe" if os.name == "nt" else "dbt"
    sibling = Path(sys.executable).with_name(executable_name)
    if sibling.exists():
        return str(sibling)

    return shutil.which("dbt") or "dbt"


def build_dbt_commands(skip_dbt: bool) -> list[list[str]]:
    if skip_dbt:
        return []

    dbt_command = resolve_dbt_command()
    project_dir = str(PROJECT_ROOT / "dbt_project")
    profiles_dir = str(PROJECT_ROOT / "dbt_project" / "profiles")

    return [
        [dbt_command, "debug", "--project-dir", project_dir, "--profiles-dir", profiles_dir],
        [dbt_command, "parse", "--project-dir", project_dir, "--profiles-dir", profiles_dir],
        [dbt_command, "run", "--project-dir", project_dir, "--profiles-dir", profiles_dir],
        [dbt_command, "test", "--project-dir", project_dir, "--profiles-dir", profiles_dir],
    ]


def run_command(command: list[str]) -> None:
    display = " ".join(command)
    print(f"Running: {display}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def list_source_files(raw_dir: Path) -> list[str]:
    return sorted(path.name for path in raw_dir.glob("*.xlsx"))


def collect_artifact_summaries(output_dir: Path) -> list[ArtifactSummary]:
    summaries: list[ArtifactSummary] = []
    missing_or_empty: list[str] = []

    for filename in EXPECTED_ARTIFACTS:
        path = output_dir / filename
        if not path.exists() or path.stat().st_size <= 0:
            missing_or_empty.append(filename)
            continue

        summaries.append(
            ArtifactSummary(
                name=filename,
                path=str(path),
                size_bytes=path.stat().st_size,
            )
        )

    if missing_or_empty:
        raise QualityGateError(
            f"Missing or empty reporting artifacts: {', '.join(missing_or_empty)}"
        )

    return summaries


def fetch_pipeline_metrics(source_files: list[str]) -> PipelineMetrics:
    if not source_files:
        return PipelineMetrics(
            source_row_counts={},
            anomaly_row_count=0,
            max_anomaly_score=0,
            critical_anomaly_count=0,
            alert_types=[],
        )

    db_config = get_database_config()
    with psycopg.connect(
        host=db_config.host,
        port=db_config.port,
        dbname=db_config.dbname,
        user=db_config.user,
        password=db_config.password,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                select source_file, count(*)::bigint as row_count
                from raw.bookmaker_bet_dump
                where source_file = any(%s)
                group by source_file
                """,
                (source_files,),
            )
            row_counts = {source_file: int(row_count) for source_file, row_count in cursor.fetchall()}

            cursor.execute(
                """
                select
                    count(*)::bigint as anomaly_row_count,
                    coalesce(max(anomaly_score), 0) as max_anomaly_score,
                    count(*) filter (where risk_band = 'critical')::bigint as critical_anomaly_count
                from reporting.anomaly_scorecard
                where source_file = any(%s)
                """,
                (source_files,),
            )
            anomaly_row_count, max_anomaly_score, critical_anomaly_count = cursor.fetchone()

            cursor.execute(
                """
                select distinct alert_type
                from reporting.alert_feed
                where source_file = any(%s)
                order by alert_type
                """,
                (source_files,),
            )
            alert_types = [row[0] for row in cursor.fetchall()]

    return PipelineMetrics(
        source_row_counts=row_counts,
        anomaly_row_count=int(anomaly_row_count),
        max_anomaly_score=float(max_anomaly_score or Decimal("0")),
        critical_anomaly_count=int(critical_anomaly_count),
        alert_types=alert_types,
    )


def validate_quality_gates(
    source_files: list[str],
    artifacts: list[ArtifactSummary],
    metrics: PipelineMetrics,
    require_demo_alerts: bool,
) -> dict[str, Any]:
    errors: list[str] = []

    if not source_files:
        errors.append("No source .xlsx files were found for the run.")

    for source_file in source_files:
        if metrics.source_row_counts.get(source_file, 0) <= 0:
            errors.append(f"No raw rows loaded for {source_file}.")

    if len(artifacts) != len(EXPECTED_ARTIFACTS):
        errors.append("Not all expected reporting artifacts were generated.")

    if metrics.anomaly_row_count <= 0:
        errors.append("Anomaly scorecard did not produce any rows.")

    if require_demo_alerts:
        missing_alerts = sorted(EXPECTED_ALERT_TYPES.difference(metrics.alert_types))
        if missing_alerts:
            errors.append(f"Demo run missing expected alert types: {', '.join(missing_alerts)}.")

        if metrics.critical_anomaly_count <= 0:
            errors.append("Demo run did not produce a critical anomaly score.")

    if errors:
        raise QualityGateError(" ".join(errors))

    return {
        "passed": True,
        "source_file_count": len(source_files),
        "artifact_count": len(artifacts),
        "require_demo_alerts": require_demo_alerts,
    }


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def build_run_summary(
    config: PipelineConfig,
    source_files: list[str],
    artifacts: list[ArtifactSummary],
    metrics: PipelineMetrics,
    quality_gates: dict[str, Any],
    dbt_skipped: bool,
) -> dict[str, Any]:
    return {
        "run_id": str(uuid4()),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": {
            "demo": config.demo,
            "raw_dir": str(config.raw_dir),
            "output_dir": str(config.output_dir),
            "replace_files": config.replace_files,
            "skip_dbt": config.skip_dbt,
            "require_demo_alerts": config.require_demo_alerts,
        },
        "source_files": source_files,
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "metrics": asdict(metrics),
        "quality_gates": quality_gates,
        "dbt": {"skipped": dbt_skipped},
    }


@task
def generate_demo_workbook(raw_dir: Path) -> None:
    output_path = raw_dir / DEMO_WORKBOOK_NAME
    run_command(
        build_python_module_command(
            "src.data_generation.create_demo_workbook",
            "--output-path",
            str(output_path),
        )
    )


@task
def apply_sql_pipeline() -> None:
    run_command(build_python_module_command("src.setup.apply_sql_pipeline"))


@task
def load_workbook_data(raw_dir: Path, replace_files: bool) -> None:
    command = build_python_module_command(
        "src.ingest.load_bookmaker_dump",
        "--raw-dir",
        str(raw_dir),
    )
    if replace_files:
        command.append("--replace-files")

    run_command(command)


@task
def export_reporting_outputs(output_dir: Path) -> None:
    run_command(
        build_python_module_command(
            "src.reporting.export_reporting_views",
            "--output-dir",
            str(output_dir),
        )
    )


@task
def generate_markdown_report(output_dir: Path) -> None:
    run_command(
        build_python_module_command(
            "src.reporting.generate_eod_report",
            "--output-path",
            str(output_dir / "eod_integrity_report.md"),
        )
    )


@task
def run_dbt_commands(skip_dbt: bool) -> bool:
    commands = build_dbt_commands(skip_dbt)
    for command in commands:
        run_command(command)
    return skip_dbt


@task
def run_quality_gates(config: PipelineConfig) -> tuple[list[str], list[ArtifactSummary], PipelineMetrics, dict[str, Any]]:
    source_files = list_source_files(config.raw_dir)
    artifacts = collect_artifact_summaries(config.output_dir)
    metrics = fetch_pipeline_metrics(source_files)
    quality_gate_result = validate_quality_gates(
        source_files=source_files,
        artifacts=artifacts,
        metrics=metrics,
        require_demo_alerts=config.require_demo_alerts,
    )
    return source_files, artifacts, metrics, quality_gate_result


@task
def write_pipeline_summary(
    config: PipelineConfig,
    source_files: list[str],
    artifacts: list[ArtifactSummary],
    metrics: PipelineMetrics,
    quality_gates: dict[str, Any],
    dbt_skipped: bool,
) -> Path:
    summary = build_run_summary(
        config=config,
        source_files=source_files,
        artifacts=artifacts,
        metrics=metrics,
        quality_gates=quality_gates,
        dbt_skipped=dbt_skipped,
    )
    output_path = config.output_dir / "pipeline_run_summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote pipeline run summary to {output_path}")
    return output_path


@flow(name="betting-data-integrity-pipeline")
def pipeline_flow(config: PipelineConfig) -> Path:
    if config.demo:
        generate_demo_workbook(config.raw_dir)

    apply_sql_pipeline()
    load_workbook_data(config.raw_dir, config.replace_files)
    export_reporting_outputs(config.output_dir)
    generate_markdown_report(config.output_dir)
    dbt_skipped = run_dbt_commands(config.skip_dbt)
    source_files, artifacts, metrics, quality_gates = run_quality_gates(config)
    return write_pipeline_summary(
        config=config,
        source_files=source_files,
        artifacts=artifacts,
        metrics=metrics,
        quality_gates=quality_gates,
        dbt_skipped=dbt_skipped,
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = config_from_args(args)
    summary_path = pipeline_flow(config)
    print(f"Pipeline completed successfully. Summary: {summary_path}")


if __name__ == "__main__":
    main()
