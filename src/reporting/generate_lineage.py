from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT, RAW_DATA_DIR

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
LINEAGE_MANIFEST_FILENAME = "data_lineage_manifest.json"
LINEAGE_REPORT_FILENAME = "data_lineage.md"


@dataclass(frozen=True)
class LineageStage:
    stage_id: str
    name: str
    layer: str
    description: str
    inputs: list[str]
    outputs: list[str]
    code_assets: list[str]
    quality_controls: list[str]


@dataclass(frozen=True)
class ArtifactInventoryItem:
    name: str
    path: str
    size_bytes: int


LINEAGE_STAGES = [
    LineageStage(
        stage_id="source_landing",
        name="Source workbook landing",
        layer="source",
        description="Bookmaker operational Excel dumps are treated as immutable source files.",
        inputs=["bookmaker Excel workbooks"],
        outputs=["data/raw/*.xlsx"],
        code_assets=["src.data_generation.create_demo_workbook"],
        quality_controls=["Raw workbooks are ignored by Git to keep private dumps out of the repo."],
    ),
    LineageStage(
        stage_id="raw_ingestion",
        name="Raw PostgreSQL ingestion",
        layer="raw",
        description="Workbook rows are loaded with source file, source row number, source UUID, and ingestion metadata.",
        inputs=["data/raw/*.xlsx"],
        outputs=["raw.bookmaker_bet_dump"],
        code_assets=["src.ingest.load_bookmaker_dump", "sql/schema/001_raw_betting_transactions.sql"],
        quality_controls=["Header validation", "Optional replace-files load mode", "Source file row counts"],
    ),
    LineageStage(
        stage_id="staging_cleaning",
        name="Staging cleanup",
        layer="stage",
        description="Operational strings are parsed into typed dates, flags, money values, odds, stakes, payouts, and race attributes.",
        inputs=["raw.bookmaker_bet_dump"],
        outputs=["stage.bookmaker_bets_clean"],
        code_assets=["sql/transformations/001_stage_bookmaker_bets_clean.sql"],
        quality_controls=["Parsing logic keeps original raw values available upstream for audit."],
    ),
    LineageStage(
        stage_id="core_modeling",
        name="Core dimensional modeling",
        layer="core",
        description="Clean source rows are modeled into reusable customer, event, bet, and payout entities.",
        inputs=["stage.bookmaker_bets_clean"],
        outputs=["core.customers", "core.events", "core.bets", "core.payouts"],
        code_assets=["sql/transformations/002_core_views.sql", "dbt_project/models/marts/*.sql"],
        quality_controls=["dbt not-null and uniqueness tests on core keys"],
    ),
    LineageStage(
        stage_id="quality_validation",
        name="Data quality validation",
        layer="quality",
        description="Reusable issue views identify duplicate bet keys, negative stakes, missing timestamps, and payout inconsistencies.",
        inputs=["core.bets", "core.payouts"],
        outputs=[
            "quality.bookmaker_bet_validation_issues",
            "quality.bookmaker_bet_validation_summary",
        ],
        code_assets=["sql/validation_checks/001_quality_views.sql", "dbt_project/models/quality/*.sql"],
        quality_controls=["Issue type counts", "dbt quality-model tests"],
    ),
    LineageStage(
        stage_id="reporting_outputs",
        name="Reporting and reconciliation",
        layer="reporting",
        description="Validated data is shaped into daily reconciliation summaries, alert feeds, and anomaly scorecards.",
        inputs=[
            "quality.bookmaker_bet_validation_issues",
            "core.bets",
            "core.payouts",
        ],
        outputs=[
            "reporting.daily_reconciliation_summary",
            "reporting.alert_feed",
            "reporting.anomaly_scorecard",
            "data/processed/*.csv",
            "eod_integrity_report.md",
        ],
        code_assets=[
            "sql/reporting/*.sql",
            "src.reporting.export_reporting_views",
            "src.reporting.generate_eod_report",
        ],
        quality_controls=["Artifact exists/non-empty gates", "dbt reporting tests", "Demo alert gates"],
    ),
    LineageStage(
        stage_id="ml_triage",
        name="ML anomaly triage",
        layer="ml",
        description="A local Isolation Forest adds a secondary model-driven outlier signal beside the explainable rule score.",
        inputs=["reporting.anomaly_scorecard"],
        outputs=["ml_anomaly_scores.csv", "ml_anomaly_report.md"],
        code_assets=["src.anomaly_detection.ml_anomaly_model"],
        quality_controls=["ML score file non-empty gate", "Demo outlier gate"],
    ),
    LineageStage(
        stage_id="portfolio_artifacts",
        name="Portfolio and operations artifacts",
        layer="artifact",
        description="Static HTML, Markdown, JSON, and CSV artifacts make the run reviewable without private data or a running service.",
        inputs=["data/processed/*.csv", "ml_anomaly_scores.csv"],
        outputs=[
            "integrity_dashboard.html",
            "pipeline_run_summary.json",
            "data_lineage_manifest.json",
            "data_lineage.md",
        ],
        code_assets=[
            "src.reporting.generate_dashboard",
            "src.reporting.generate_lineage",
            "src.orchestration.run_pipeline",
        ],
        quality_controls=["Prefect task ordering", "Post-pipeline artifact quality gates", "GitHub Actions artifact upload"],
    ),
]


ARTIFACT_PURPOSES = {
    "daily_reconciliation_summary.csv": "Finance-ready source-day reconciliation totals and review status.",
    "daily_issue_summary.csv": "Issue counts by source file, day, and validation rule.",
    "daily_bookmaker_summary.csv": "Bookmaker-day operational and financial summary.",
    "alert_feed.csv": "Actionable rule-based alert events for integrity operations.",
    "alert_summary.csv": "Aggregated alert counts by scope, severity, and alert type.",
    "anomaly_scorecard.csv": "Explainable source-day anomaly ranking with drivers and recommended actions.",
    "eod_integrity_report.md": "Markdown executive report for end-of-day review.",
    "ml_anomaly_scores.csv": "Isolation Forest source-day ML scores with rule score comparison.",
    "ml_anomaly_report.md": "Markdown summary of ML model scoring behavior.",
    "integrity_dashboard.html": "Static portfolio dashboard for browser-based review.",
    "pipeline_run_summary.json": "Machine-readable orchestration run summary and quality-gate result.",
    "data_lineage_manifest.json": "Machine-readable lineage manifest for the pipeline.",
    "data_lineage.md": "Human-readable data lineage report.",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate machine-readable and Markdown data lineage artifacts."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing source .xlsx files for this run.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing generated reporting artifacts.",
    )
    parser.add_argument(
        "--skip-ml",
        action="store_true",
        help="Mark ML lineage outputs as skipped for this run.",
    )
    return parser.parse_args(argv)


def list_source_files(raw_dir: Path) -> list[str]:
    return sorted(path.name for path in raw_dir.glob("*.xlsx"))


def collect_artifact_inventory(output_dir: Path) -> list[ArtifactInventoryItem]:
    inventory: list[ArtifactInventoryItem] = []
    if not output_dir.exists():
        return inventory

    for path in sorted(output_dir.iterdir()):
        if not path.is_file():
            continue

        inventory.append(
            ArtifactInventoryItem(
                name=path.name,
                path=str(path),
                size_bytes=path.stat().st_size,
            )
        )

    return inventory


def build_artifact_lineage(inventory: list[ArtifactInventoryItem]) -> list[dict[str, Any]]:
    return [
        {
            "artifact": item.name,
            "path": item.path,
            "size_bytes": item.size_bytes,
            "purpose": ARTIFACT_PURPOSES.get(item.name, "Generated pipeline artifact."),
        }
        for item in inventory
    ]


def build_lineage_manifest(
    raw_dir: Path,
    output_dir: Path,
    skip_ml: bool = False,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    inventory = collect_artifact_inventory(output_dir)
    stages = [asdict(stage) for stage in LINEAGE_STAGES]
    if skip_ml:
        for stage in stages:
            if stage["stage_id"] == "ml_triage":
                stage["description"] += " This stage was skipped for the current run."
                stage["outputs"] = []
                stage["quality_controls"] = ["Skipped by --skip-ml."]

    return {
        "generated_at": (generated_at or datetime.now()).isoformat(timespec="seconds"),
        "pipeline_name": "betting-data-integrity-pipeline",
        "lineage_version": "1.0",
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "source_files": list_source_files(raw_dir),
        "stages": stages,
        "artifact_inventory": [asdict(item) for item in inventory],
        "artifact_lineage": build_artifact_lineage(inventory),
    }


def render_list(items: list[str]) -> str:
    if not items:
        return "_None for this run._"
    return "\n".join(f"- `{item}`" for item in items)


def render_markdown_report(manifest: dict[str, Any]) -> str:
    source_files = manifest["source_files"]
    inventory = manifest["artifact_inventory"]

    lines = [
        "# Data Lineage Report",
        "",
        f"Generated at: `{manifest['generated_at']}`",
        "",
        "## Run Scope",
        "",
        f"- Pipeline: `{manifest['pipeline_name']}`",
        f"- Lineage version: `{manifest['lineage_version']}`",
        f"- Raw directory: `{manifest['raw_dir']}`",
        f"- Output directory: `{manifest['output_dir']}`",
        f"- Source files: `{len(source_files)}`",
        f"- Generated artifacts inventoried: `{len(inventory)}`",
        "",
        "## Source Files",
        "",
        render_list(source_files),
        "",
        "## Lineage Flow",
        "",
        "```mermaid",
        "flowchart LR",
        '  A["Excel workbooks"] --> B["raw.bookmaker_bet_dump"]',
        '  B --> C["stage.bookmaker_bets_clean"]',
        '  C --> D["core models"]',
        '  D --> E["quality checks"]',
        '  E --> F["reporting views"]',
        '  F --> G["CSV / Markdown outputs"]',
        '  F --> H["ML anomaly scoring"]',
        '  G --> I["HTML dashboard"]',
        '  H --> I',
        '  I --> J["lineage + run summary artifacts"]',
        "```",
        "",
        "## Processing Stages",
        "",
    ]

    for stage in manifest["stages"]:
        lines.extend(
            [
                f"### {stage['name']}",
                "",
                f"- Stage ID: `{stage['stage_id']}`",
                f"- Layer: `{stage['layer']}`",
                f"- Description: {stage['description']}",
                "- Inputs:",
                render_list(stage["inputs"]),
                "- Outputs:",
                render_list(stage["outputs"]),
                "- Code assets:",
                render_list(stage["code_assets"]),
                "- Quality controls:",
                render_list(stage["quality_controls"]),
                "",
            ]
        )

    lines.extend(["## Artifact Inventory", ""])
    if inventory:
        lines.extend(
            [
                "| artifact | size_bytes | purpose |",
                "| --- | ---: | --- |",
            ]
        )
        for item in manifest["artifact_lineage"]:
            lines.append(
                f"| `{item['artifact']}` | {item['size_bytes']} | {item['purpose']} |"
            )
    else:
        lines.append("_No generated artifacts found._")

    return "\n".join(lines) + "\n"


def write_lineage_artifacts(
    raw_dir: Path,
    output_dir: Path,
    skip_ml: bool = False,
) -> tuple[Path, Path]:
    manifest = build_lineage_manifest(raw_dir=raw_dir, output_dir=output_dir, skip_ml=skip_ml)
    manifest_path = output_dir / LINEAGE_MANIFEST_FILENAME
    report_path = output_dir / LINEAGE_REPORT_FILENAME
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_markdown_report(manifest), encoding="utf-8")
    return manifest_path, report_path


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    manifest_path, report_path = write_lineage_artifacts(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        skip_ml=args.skip_ml,
    )
    print(f"Wrote data lineage manifest to {manifest_path}")
    print(f"Wrote data lineage report to {report_path}")


if __name__ == "__main__":
    main()
