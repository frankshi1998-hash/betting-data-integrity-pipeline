from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from src.config import PROJECT_ROOT, get_database_config

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "eod_integrity_report.md"

OVERVIEW_QUERY = """
with scorecard as (
    select *
    from reporting.anomaly_scorecard
)
select
    count(*) as source_day_count,
    coalesce(sum(total_bet_rows), 0)::bigint as total_bet_rows,
    count(*) filter (where reconciliation_status = 'review') as review_source_day_count,
    count(*) filter (where risk_band in ('critical', 'high')) as high_risk_source_day_count,
    coalesce(sum(total_stake_amount), 0) as total_stake_amount,
    coalesce(sum(total_payout_amount), 0) as total_payout_amount,
    coalesce(sum(net_revenue_amount), 0) as net_revenue_amount,
    coalesce(max(anomaly_score), 0) as max_anomaly_score,
    (select count(*) from reporting.alert_feed) as total_alert_count,
    (select count(*) from quality.bookmaker_bet_validation_issues) as total_quality_issue_count
from scorecard
"""

RISK_BAND_QUERY = """
select
    risk_band,
    count(*) as source_day_count,
    max(anomaly_score) as max_anomaly_score
from reporting.anomaly_scorecard
group by risk_band
order by
    case risk_band
        when 'critical' then 1
        when 'high' then 2
        when 'medium' then 3
        when 'low' then 4
        else 5
    end
"""

TOP_ANOMALIES_QUERY = """
select
    report_date,
    source_file,
    anomaly_score,
    risk_band,
    primary_driver,
    recommended_action,
    total_bet_rows::bigint as total_bet_rows,
    total_issue_rows::bigint as total_issue_rows,
    alert_count::bigint as alert_count,
    payout_ratio
from reporting.anomaly_scorecard
where anomaly_score > 0
order by anomaly_score desc, report_date desc, source_file
limit 10
"""

ALERT_SUMMARY_QUERY = """
select
    severity,
    alert_type,
    count(*) as alert_count
from reporting.alert_feed
group by severity, alert_type
order by
    case severity
        when 'critical' then 1
        when 'high' then 2
        when 'medium' then 3
        else 4
    end,
    alert_type
"""

QUALITY_ISSUE_QUERY = """
select
    issue_type,
    count(*) as issue_count
from quality.bookmaker_bet_validation_issues
group by issue_type
order by issue_count desc, issue_type
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown EOD betting integrity report from reporting views."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Markdown report path to write.",
    )
    return parser.parse_args()


def fetch_rows(conn: psycopg.Connection, query: str) -> list[dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(query)
        headers = [column.name for column in cursor.description]
        return [dict(zip(headers, row)) for row in cursor.fetchall()]


def format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value)


def render_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No rows found._"

    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = [
        "| " + " | ".join(format_value(row.get(header)) for header in headers) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator_line, *body_lines])


def render_markdown_report(
    generated_at: datetime,
    overview: dict[str, Any],
    risk_bands: list[dict[str, Any]],
    top_anomalies: list[dict[str, Any]],
    alert_summary: list[dict[str, Any]],
    quality_issues: list[dict[str, Any]],
) -> str:
    return "\n\n".join(
        [
            "# EOD Betting Integrity Report",
            f"Generated at: `{generated_at.isoformat(timespec='seconds')}`",
            "## Executive Summary\n"
            f"- Source-days reviewed: `{format_value(overview.get('source_day_count'))}`\n"
            f"- Total bet rows: `{format_value(overview.get('total_bet_rows'))}`\n"
            f"- Source-days requiring review: `{format_value(overview.get('review_source_day_count'))}`\n"
            f"- High-risk source-days: `{format_value(overview.get('high_risk_source_day_count'))}`\n"
            f"- Alerts generated: `{format_value(overview.get('total_alert_count'))}`\n"
            f"- Quality issue rows: `{format_value(overview.get('total_quality_issue_count'))}`\n"
            f"- Max anomaly score: `{format_value(overview.get('max_anomaly_score'))}`\n"
            f"- Total stake: `${format_value(overview.get('total_stake_amount'))}`\n"
            f"- Total payout: `${format_value(overview.get('total_payout_amount'))}`\n"
            f"- Net revenue: `${format_value(overview.get('net_revenue_amount'))}`",
            "## Risk Bands\n"
            + render_table(
                ["risk_band", "source_day_count", "max_anomaly_score"],
                risk_bands,
            ),
            "## Top Anomaly Priorities\n"
            + render_table(
                [
                    "report_date",
                    "source_file",
                    "anomaly_score",
                    "risk_band",
                    "primary_driver",
                    "recommended_action",
                    "total_bet_rows",
                    "total_issue_rows",
                    "alert_count",
                    "payout_ratio",
                ],
                top_anomalies,
            ),
            "## Alert Summary\n"
            + render_table(
                ["severity", "alert_type", "alert_count"],
                alert_summary,
            ),
            "## Quality Issue Summary\n"
            + render_table(
                ["issue_type", "issue_count"],
                quality_issues,
            ),
        ]
    ) + "\n"


def main() -> None:
    args = parse_args()
    db_config = get_database_config()

    with psycopg.connect(
        host=db_config.host,
        port=db_config.port,
        dbname=db_config.dbname,
        user=db_config.user,
        password=db_config.password,
    ) as conn:
        overview_rows = fetch_rows(conn, OVERVIEW_QUERY)
        report = render_markdown_report(
            generated_at=datetime.now(),
            overview=overview_rows[0] if overview_rows else {},
            risk_bands=fetch_rows(conn, RISK_BAND_QUERY),
            top_anomalies=fetch_rows(conn, TOP_ANOMALIES_QUERY),
            alert_summary=fetch_rows(conn, ALERT_SUMMARY_QUERY),
            quality_issues=fetch_rows(conn, QUALITY_ISSUE_QUERY),
        )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(report, encoding="utf-8")
    print(f"Wrote EOD integrity report to {args.output_path}")


if __name__ == "__main__":
    main()
