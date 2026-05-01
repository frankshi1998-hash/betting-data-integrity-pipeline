from __future__ import annotations

import argparse
import csv
from pathlib import Path

import psycopg

from src.config import PROJECT_ROOT, get_database_config

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

EXPORT_SPECS = [
    (
        "daily_reconciliation_summary.csv",
        """
        select *
        from reporting.daily_reconciliation_summary
        order by report_date, source_file
        """,
    ),
    (
        "daily_issue_summary.csv",
        """
        select *
        from reporting.daily_issue_summary
        order by report_date, source_file, issue_type
        """,
    ),
    (
        "daily_bookmaker_summary.csv",
        """
        select *
        from reporting.daily_bookmaker_summary
        order by report_date, bookmaker_name
        """,
    ),
    (
        "alert_feed.csv",
        """
        select *
        from reporting.alert_feed
        order by report_date, alert_scope, severity desc, alert_type, coalesce(source_file, bookmaker_name)
        """,
    ),
    (
        "alert_summary.csv",
        """
        select *
        from reporting.alert_summary
        order by report_date, alert_scope, severity, alert_type
        """,
    ),
    (
        "anomaly_scorecard.csv",
        """
        select *
        from reporting.anomaly_scorecard
        order by report_date, anomaly_score desc, source_file
        """,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export reporting views to CSV files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where CSV files will be written.",
    )
    return parser.parse_args()


def export_query_to_csv(
    conn: psycopg.Connection,
    query: str,
    output_path: Path,
) -> int:
    with conn.cursor() as cursor:
        cursor.execute(query)
        headers = [column.name for column in cursor.description]
        rows = cursor.fetchall()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(rows)

    return len(rows)


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
        for filename, query in EXPORT_SPECS:
            output_path = args.output_dir / filename
            row_count = export_query_to_csv(conn, query, output_path)
            print(f"Exported {row_count} rows to {output_path}")


if __name__ == "__main__":
    main()
