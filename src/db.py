"""
SQLite helpers (init, read, write) used by the scraper and API.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from . import paths

DB_PATH = paths.DATA_DIR / "database.sqlite"


def resolve_db_path(db_path: Optional[Path] = None) -> Path:
    return Path(db_path) if db_path is not None else DB_PATH


def init_db(db_path: Optional[Path] = None) -> Path:
    """
    Create the prices table and index if missing.
    Returns the resolved DB path.
    """
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                product_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                category TEXT,
                price REAL,
                status TEXT NOT NULL DEFAULT 'ok',
                error TEXT,
                currency TEXT,
                scraped_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_prices_product_time
            ON prices (site_name, product_code, scraped_at)
            """
        )
        _ensure_currency_column(conn)
        conn.commit()
    finally:
        conn.close()

    return path


def _ensure_currency_column(conn: sqlite3.Connection) -> None:
    """Add currency column if missing (lightweight migration)."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(prices)")
    cols = [row[1] for row in cur.fetchall()]
    if "currency" not in cols:
        cur.execute("ALTER TABLE prices ADD COLUMN currency TEXT")
        cur.execute("UPDATE prices SET currency = 'USD' WHERE currency IS NULL OR currency = ''")


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a sqlite3 connection."""
    return sqlite3.connect(resolve_db_path(db_path))


def store_price(
    conn: sqlite3.Connection,
    *,
    site_name: str,
    product_code: str,
    product_name: str,
    category: str,
    price: float | None,
    status: str = "ok",
    error: Optional[str] = None,
    currency: Optional[str] = "USD",
    scraped_at: Optional[datetime] = None,
) -> None:
    """Insert a single price row."""
    if scraped_at is None:
        scraped_at = datetime.now()

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO prices (
            site_name,
            product_code,
            product_name,
            category,
            price,
            status,
            error,
            currency,
            scraped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            site_name,
            product_code,
            product_name,
            category,
            float(price) if price is not None else None,
            status,
            error,
            currency,
            scraped_at.isoformat(),
        ),
    )


def load_all_history(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Read full price history as a DataFrame."""
    path = resolve_db_path(db_path)
    if not path.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            """
            SELECT
                site_name,
                product_code,
                product_name,
                category,
                price,
                status,
                error,
                currency,
                scraped_at
            FROM prices
            ORDER BY scraped_at ASC
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    return df


def load_price_history(
    days: int = 30,
    db_path: Optional[Path] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> pd.DataFrame:
    """Read history limited to the last N days with optional pagination."""
    path = resolve_db_path(db_path)
    if not path.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            """
            SELECT
                site_name,
                product_code,
                product_name,
                category,
                price,
                status,
                error,
                currency,
                scraped_at
            FROM prices
            ORDER BY scraped_at ASC
            """,
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return df

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    latest_ts = df["scraped_at"].max()
    since = latest_ts - pd.Timedelta(days=days)
    df = df[df["scraped_at"] >= since]

    if offset or limit:
        df = df.sort_values("scraped_at").iloc[offset : offset + limit if limit else None]

    # Keep only successful rows for numeric stats, but return overall DataFrame when none
    ok_df = df[(df.get("status") == "ok") & df["price"].notna()]
    if not ok_df.empty:
        return ok_df
    return df


def load_latest_prices(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Return the latest price per (site_name, product_code)."""
    history_df = load_all_history(db_path=db_path)
    if history_df.empty:
        return pd.DataFrame()

    history_df = history_df.sort_values("scraped_at")
    latest_df = history_df.drop_duplicates(
        subset=["site_name", "product_code"],
        keep="last",
    )
    return latest_df.reset_index(drop=True)
