from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from src.config import PROJECT_ROOT, get_database_config

SQL_FILES = [
    PROJECT_ROOT / 'sql' / 'schema' / '001_raw_betting_transactions.sql',
    PROJECT_ROOT / 'sql' / 'schema' / '002_stage_support.sql',
    PROJECT_ROOT / 'sql' / 'transformations' / '001_stage_bookmaker_bets_clean.sql',
    PROJECT_ROOT / 'sql' / 'transformations' / '002_core_views.sql',
    PROJECT_ROOT / 'sql' / 'validation_checks' / '001_quality_views.sql',
    PROJECT_ROOT / 'sql' / 'reporting' / '001_eod_reconciliation_views.sql',
    PROJECT_ROOT / 'sql' / 'reporting' / '002_alert_views.sql',
]

PREPARE_SQL = [
    "drop view if exists reporting.alert_summary;",
    "drop view if exists reporting.alert_feed;",
    "drop view if exists reporting.bookmaker_day_alerts;",
    "drop view if exists reporting.source_day_alerts;",
    "drop view if exists reporting.daily_reconciliation_summary;",
    "drop view if exists reporting.daily_bookmaker_summary;",
    "drop view if exists reporting.daily_issue_summary;",
    "drop view if exists quality.bookmaker_bet_validation_summary;",
    "drop view if exists quality.bookmaker_bet_validation_issues;",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Apply the SQL pipeline to the configured PostgreSQL database.'
    )
    parser.add_argument(
        '--stop-after',
        type=str,
        default=None,
        help='Optional filename to stop after applying, for debugging.',
    )
    return parser.parse_args()


def apply_sql_file(cursor: psycopg.Cursor, path: Path) -> None:
    sql_text = path.read_text(encoding='utf-8')
    cursor.execute(sql_text)


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
        with conn.cursor() as cursor:
            for statement in PREPARE_SQL:
                cursor.execute(statement)

            for sql_file in SQL_FILES:
                if not sql_file.exists():
                    raise FileNotFoundError(f'Missing SQL file: {sql_file}')

                print(f'Applying {sql_file.name}')
                apply_sql_file(cursor, sql_file)

                if args.stop_after and sql_file.name == args.stop_after:
                    break

        conn.commit()

    print('SQL pipeline applied successfully.')


if __name__ == '__main__':
    main()
