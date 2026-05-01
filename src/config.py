from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema" / "001_raw_betting_transactions.sql"
ENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str


def load_environment() -> None:
    if not ENV_PATH.exists():
        return

    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return

    load_dotenv(ENV_PATH)


def get_database_config() -> DatabaseConfig:
    load_environment()

    return DatabaseConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "xid_go"),
        user=os.getenv("PGUSER", "xid_user"),
        password=os.getenv("PGPASSWORD", "xid_password"),
    )

