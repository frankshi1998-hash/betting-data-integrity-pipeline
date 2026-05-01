from __future__ import annotations

import argparse
import csv
import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.config import PROJECT_ROOT, get_database_config

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
ML_SCORE_FILENAME = "ml_anomaly_scores.csv"
ML_REPORT_FILENAME = "ml_anomaly_report.md"
MODEL_NAME = "isolation_forest_source_day_v1"
RANDOM_STATE = 42


@dataclass(frozen=True)
class FeatureSpec:
    column: str
    label: str
    transform: str = "identity"


FEATURE_SPECS = [
    FeatureSpec("anomaly_score", "rule anomaly score"),
    FeatureSpec("duplicate_ratio", "duplicate pressure"),
    FeatureSpec("negative_stake_ratio", "negative stake pressure"),
    FeatureSpec("issue_ratio", "quality issue density"),
    FeatureSpec("payout_ratio", "payout ratio pressure"),
    FeatureSpec("total_bet_rows", "bet volume", "log1p"),
    FeatureSpec("total_issue_rows", "issue volume", "log1p"),
    FeatureSpec("alert_count", "alert volume", "log1p"),
    FeatureSpec("critical_alert_count", "critical alert volume", "log1p"),
    FeatureSpec("net_revenue_amount", "net revenue movement", "signed_log1p"),
]

OUTPUT_COLUMNS = [
    "ml_score_id",
    "model_name",
    "source_file",
    "report_date",
    "rule_anomaly_score",
    "rule_risk_band",
    "ml_anomaly_score",
    "ml_risk_band",
    "model_outlier_flag",
    "model_driver",
    "primary_driver",
    "recommended_action",
    "total_bet_rows",
    "total_issue_rows",
    "alert_count",
    "duplicate_ratio",
    "negative_stake_ratio",
    "issue_ratio",
    "payout_ratio",
    "net_revenue_amount",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a lightweight ML anomaly model and export source-day scores."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where ML anomaly artifacts are written.",
    )
    return parser.parse_args(argv)


def to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def transform_value(value: Any, transform: str) -> float:
    numeric_value = to_float(value)
    if transform == "log1p":
        return math.log1p(max(numeric_value, 0.0))
    if transform == "signed_log1p":
        sign = -1.0 if numeric_value < 0 else 1.0
        return sign * math.log1p(abs(numeric_value))
    return numeric_value


def fetch_scorecard_rows() -> list[dict[str, Any]]:
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
                select
                    anomaly_id,
                    source_file,
                    report_date::text as report_date,
                    anomaly_score,
                    risk_band,
                    primary_driver,
                    recommended_action,
                    total_bet_rows,
                    total_issue_rows,
                    duplicate_ratio,
                    negative_stake_ratio,
                    issue_ratio,
                    payout_ratio,
                    alert_count,
                    critical_alert_count,
                    net_revenue_amount
                from reporting.anomaly_scorecard
                order by report_date, source_file
                """
            )
            headers = [column.name for column in cursor.description]
            return [dict(zip(headers, row)) for row in cursor.fetchall()]


def build_feature_matrix(rows: list[dict[str, Any]]) -> list[list[float]]:
    return [
        [
            transform_value(row.get(feature.column), feature.transform)
            for feature in FEATURE_SPECS
        ]
        for row in rows
    ]


def normalize_scores(raw_scores: list[float], fallback_scores: list[float]) -> list[float]:
    if not raw_scores:
        return []

    min_score = min(raw_scores)
    max_score = max(raw_scores)
    if math.isclose(min_score, max_score):
        return [round(max(0.0, min(100.0, score)), 4) for score in fallback_scores]

    span = max_score - min_score
    return [round(((score - min_score) / span) * 100, 4) for score in raw_scores]


def risk_band(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    if score >= 15:
        return "low"
    return "normal"


def robust_feature_drivers(feature_matrix: list[list[float]]) -> list[str]:
    if not feature_matrix:
        return []

    columns = list(zip(*feature_matrix))
    medians = [statistics.median(column) for column in columns]
    mads = [
        statistics.median(abs(value - medians[index]) for value in column) or 1.0
        for index, column in enumerate(columns)
    ]

    drivers: list[str] = []
    for feature_values in feature_matrix:
        deviation_scores = [
            abs(value - medians[index]) / mads[index]
            for index, value in enumerate(feature_values)
        ]
        driver_index = max(range(len(deviation_scores)), key=deviation_scores.__getitem__)
        drivers.append(FEATURE_SPECS[driver_index].label)

    return drivers


def recommended_ml_action(
    model_outlier_flag: bool,
    ml_risk_band: str,
    rule_risk_band: str,
) -> str:
    if model_outlier_flag and rule_risk_band in {"critical", "high"}:
        return "Investigate immediately; ML agrees with rule-based anomaly pressure"
    if model_outlier_flag:
        return "Review model-only anomaly against raw transactions"
    if ml_risk_band in {"medium", "high"}:
        return "Monitor during daily reconciliation"
    return "No ML action required"


def build_score_id(row: dict[str, Any]) -> str:
    stable_key = f"{MODEL_NAME}|{row['source_file']}|{row['report_date']}"
    return hashlib.md5(stable_key.encode("utf-8")).hexdigest()


def score_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    feature_matrix = build_feature_matrix(rows)
    fallback_scores = [to_float(row.get("anomaly_score")) for row in rows]

    if len(rows) < 4:
        normalized_model_scores = normalize_scores(fallback_scores, fallback_scores)
        predictions = [-1 if score >= 80 else 1 for score in normalized_model_scores]
    else:
        scaled_features = StandardScaler().fit_transform(feature_matrix)
        contamination = min(0.2, max(1 / len(rows), 0.05))
        model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=RANDOM_STATE,
        )
        predictions = model.fit_predict(scaled_features).tolist()
        raw_model_scores = (-model.decision_function(scaled_features)).tolist()
        normalized_model_scores = normalize_scores(raw_model_scores, fallback_scores)

    drivers = robust_feature_drivers(feature_matrix)
    scored_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        ml_score = normalized_model_scores[index]
        band = risk_band(ml_score)
        outlier_flag = predictions[index] == -1 or ml_score >= 80
        rule_risk_band = str(row["risk_band"])
        output_row = {
            "ml_score_id": build_score_id(row),
            "model_name": MODEL_NAME,
            "source_file": row["source_file"],
            "report_date": row["report_date"],
            "rule_anomaly_score": round(to_float(row["anomaly_score"]), 4),
            "rule_risk_band": rule_risk_band,
            "ml_anomaly_score": ml_score,
            "ml_risk_band": band,
            "model_outlier_flag": outlier_flag,
            "model_driver": drivers[index],
            "primary_driver": row["primary_driver"],
            "recommended_action": recommended_ml_action(outlier_flag, band, rule_risk_band),
            "total_bet_rows": int(to_float(row.get("total_bet_rows"))),
            "total_issue_rows": int(to_float(row.get("total_issue_rows"))),
            "alert_count": int(to_float(row.get("alert_count"))),
            "duplicate_ratio": round(to_float(row.get("duplicate_ratio")), 4),
            "negative_stake_ratio": round(to_float(row.get("negative_stake_ratio")), 4),
            "issue_ratio": round(to_float(row.get("issue_ratio")), 4),
            "payout_ratio": round(to_float(row.get("payout_ratio")), 4),
            "net_revenue_amount": round(to_float(row.get("net_revenue_amount")), 2),
        }
        scored_rows.append(output_row)

    return sorted(
        scored_rows,
        key=lambda item: (item["ml_anomaly_score"], item["rule_anomaly_score"]),
        reverse=True,
    )


def write_scores_csv(scored_rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in scored_rows:
            writer.writerow(row)


def render_markdown_report(
    scored_rows: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    total_rows = len(scored_rows)
    outlier_count = sum(1 for row in scored_rows if row["model_outlier_flag"])
    max_score = max((row["ml_anomaly_score"] for row in scored_rows), default=0.0)
    top_rows = scored_rows[:5]
    feature_list = ", ".join(feature.label for feature in FEATURE_SPECS)

    lines = [
        "# ML Anomaly Model Report",
        "",
        f"Generated at: `{generated_at.isoformat(timespec='seconds')}`",
        "",
        "## Model Summary",
        "",
        f"- Model: `{MODEL_NAME}`",
        f"- Rows scored: `{total_rows}`",
        f"- Model outliers: `{outlier_count}`",
        f"- Max ML anomaly score: `{max_score:.2f}`",
        "",
        "The model is an unsupervised Isolation Forest over source-day reconciliation features. It is a secondary triage signal; the explainable rule scorecard remains the operational source of truth.",
        "",
        "## Features",
        "",
        feature_list,
        "",
        "## Top ML Anomaly Priorities",
        "",
    ]

    if not top_rows:
        lines.append("_No source-day rows were available for ML scoring._")
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "| report_date | source_file | ml_score | ml_risk | rule_score | rule_risk | model_driver | action |",
            "| --- | --- | ---: | --- | ---: | --- | --- | --- |",
        ]
    )
    for row in top_rows:
        lines.append(
            "| {report_date} | {source_file} | {ml_anomaly_score:.2f} | {ml_risk_band} | "
            "{rule_anomaly_score:.2f} | {rule_risk_band} | {model_driver} | {recommended_action} |".format(
                **row
            )
        )

    return "\n".join(lines) + "\n"


def write_report(scored_rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown_report(scored_rows, datetime.now()),
        encoding="utf-8",
    )


def run_ml_scoring(output_dir: Path) -> tuple[Path, Path, int]:
    rows = fetch_scorecard_rows()
    scored_rows = score_rows(rows)
    scores_path = output_dir / ML_SCORE_FILENAME
    report_path = output_dir / ML_REPORT_FILENAME
    write_scores_csv(scored_rows, scores_path)
    write_report(scored_rows, report_path)
    return scores_path, report_path, len(scored_rows)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    scores_path, report_path, row_count = run_ml_scoring(args.output_dir)
    print(f"Wrote {row_count} ML anomaly scores to {scores_path}")
    print(f"Wrote ML anomaly report to {report_path}")


if __name__ == "__main__":
    main()
