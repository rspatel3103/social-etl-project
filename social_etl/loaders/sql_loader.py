"""
SQL Server loader.

This module contains functions for writing transformed insights data
into a Microsoft SQL Server database. The target connection details
are read from the ``SQL_CONN_STR`` environment variable to avoid
hard coding credentials. Each platform writes into its own table,
named ``{platform}_insights_daily``, with a common schema across all
platforms. The schema includes a primary key ``fetch_date`` (DATE)
and integer columns for each standard metric. If the table does not
exist, it is created automatically.

Data is loaded via a MERGE statement which either inserts a new
record for the current date or updates the existing row if one
already exists. This ensures that running the ETL multiple times per
day will upsert the most recent metrics without creating duplicate
rows.

NOTE (2025-11): For the Google Analytics table **GA_insights_daily** only,
we extend the schema with GA-specific columns (nullable):
    sessions (INT), new_users (INT),
    engagement_rate (DECIMAL(6,4)),
    avg_session_duration_sec (DECIMAL(12,2)),
    events_per_session (DECIMAL(10,4))
Other platform tables are NOT changed.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, Optional

import pyodbc


# ------------------------------ Connection ------------------------------ #

def _get_connection() -> pyodbc.Connection:
    """Create a new connection to the SQL Server using ``SQL_CONN_STR``."""
    conn_str = os.getenv("SQL_CONN_STR")
    if not conn_str:
        raise EnvironmentError(
            "SQL_CONN_STR is not set. Define it in your environment or .env file."
        )
    return pyodbc.connect(conn_str)


# ------------------------------ Helpers ------------------------------ #

def _is_ga_table(table_name: str) -> bool:
    # Treat *exactly* GA_insights_daily (case-insensitive) as the GA table
    return table_name.strip().lower() == "ga_insights_daily"


def _column_exists(cursor: pyodbc.Cursor, table_name: str, col_name: str) -> bool:
    cursor.execute("""
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
    """, (table_name, col_name))
    return cursor.fetchone() is not None


def _table_exists(cursor: pyodbc.Cursor, table_name: str) -> bool:
    cursor.execute("""
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = ?
    """, (table_name,))
    return cursor.fetchone() is not None


def _ensure_ga_columns(cursor: pyodbc.Cursor, table_name: str) -> None:
    """Add GA-only columns to GA_insights_daily if any are missing (nullable)."""
    ga_cols = [
        ("sessions", "INT"),
        ("new_users", "INT"),
        ("engagement_rate", "DECIMAL(6,4)"),
        ("avg_session_duration_sec", "DECIMAL(12,2)"),
        ("events_per_session", "DECIMAL(10,4)"),
        # key_events removed
    ]
    for col, typ in ga_cols:
        if not _column_exists(cursor, table_name, col):
            cursor.execute(f"ALTER TABLE [{table_name}] ADD {col} {typ} NULL;")


def _round2(x: Optional[float]) -> float:
    try:
        return round(float(x or 0.0), 2)
    except Exception:
        return 0.0


def _round4(x: Optional[float]) -> float:
    try:
        return round(float(x or 0.0), 4)
    except Exception:
        return 0.0


# ------------------------------ DDL Ensure ------------------------------ #

def ensure_table_exists(cursor: pyodbc.Cursor, table_name: str) -> None:
    """Ensure the target table exists for the given platform.

    Non-GA tables: 5 standard columns.
    GA_insights_daily: same base + GA extras (added if missing).
    """
    safe_table = f"[{table_name}]"

    if not _table_exists(cursor, table_name):
        # Base table create (5 standard columns)
        cursor.execute(f"""
            CREATE TABLE {safe_table} (
                fetch_date DATE PRIMARY KEY,
                reach INT,
                profile_views INT,
                accounts_engaged INT,
                website_clicks INT,
                total_interactions INT,
                created_at DATETIME
            )
        """)
        # If it's GA, immediately extend with GA nullable columns
        if _is_ga_table(table_name):
            _ensure_ga_columns(cursor, table_name)
        return

    # Table exists already. If GA, add any missing GA columns (nullable).
    if _is_ga_table(table_name):
        _ensure_ga_columns(cursor, table_name)


# ------------------------------ Upsert ------------------------------ #

def load_to_sql(data: Dict[str, Any], platform: str) -> None:
    """Load transformed data into the SQL Server table for a platform.

    For GA, the payload may include:
      sessions, new_users, engagement_rate, avg_session_duration_sec, events_per_session
    """
    table_name = f"{platform}_insights_daily"
    is_ga = _is_ga_table(table_name)

    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # Ensure table exists (and only extend GA table if needed)
        ensure_table_exists(cursor, table_name)

        fetch_date = datetime.today().date()
        created_at = datetime.now()
        safe_table = f"[{table_name}]"

        if not is_ga:
            # --- Non-GA platforms: original MERGE (5 columns) ---
            sql = f"""
                MERGE {safe_table} AS target
                USING (SELECT ? AS fetch_date) AS source
                ON target.fetch_date = source.fetch_date
                WHEN MATCHED THEN UPDATE SET
                    reach = ?, profile_views = ?, accounts_engaged = ?,
                    website_clicks = ?, total_interactions = ?, created_at = ?
                WHEN NOT MATCHED THEN
                    INSERT (fetch_date, reach, profile_views, accounts_engaged, website_clicks, total_interactions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            params = (
                fetch_date,
                int(data.get("reach", 0)),
                int(data.get("profile_views", 0)),
                int(data.get("accounts_engaged", 0)),
                int(data.get("website_clicks", 0)),
                int(data.get("total_interactions", 0)),
                created_at,
                fetch_date,
                int(data.get("reach", 0)),
                int(data.get("profile_views", 0)),
                int(data.get("accounts_engaged", 0)),
                int(data.get("website_clicks", 0)),
                int(data.get("total_interactions", 0)),
                created_at,
            )
            cursor.execute(sql, params)
            conn.commit()
            return

        # --- GA table: extended MERGE with GA extras (nullable) ---
        sessions = data.get("sessions", None)
        new_users = data.get("new_users", None)
        engagement_rate = data.get("engagement_rate", None)
        avg_sess_dur = data.get("avg_session_duration_sec", None)
        events_per_session = data.get("events_per_session", None)

        sessions = int(sessions) if sessions is not None else None
        new_users = int(new_users) if new_users is not None else None
        engagement_rate = _round4(engagement_rate) if engagement_rate is not None else None
        avg_sess_dur = _round2(avg_sess_dur) if avg_sess_dur is not None else None
        events_per_session = _round4(events_per_session) if events_per_session is not None else None

        sql_ga = f"""
            MERGE {safe_table} AS target
            USING (SELECT ? AS fetch_date) AS source
            ON target.fetch_date = source.fetch_date
            WHEN MATCHED THEN UPDATE SET
                reach = ?, profile_views = ?, accounts_engaged = ?,
                website_clicks = ?, total_interactions = ?, created_at = ?,
                sessions = ?, new_users = ?, engagement_rate = ?,
                avg_session_duration_sec = ?, events_per_session = ?
            WHEN NOT MATCHED THEN
                INSERT (
                    fetch_date, reach, profile_views, accounts_engaged, website_clicks, total_interactions, created_at,
                    sessions, new_users, engagement_rate, avg_session_duration_sec, events_per_session
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        params_ga = (
            # MATCHED (update)
            fetch_date,
            int(data.get("reach", 0)),
            int(data.get("profile_views", 0)),
            int(data.get("accounts_engaged", 0)),
            int(data.get("website_clicks", 0)),
            int(data.get("total_interactions", 0)),
            created_at,
            sessions, new_users, engagement_rate, avg_sess_dur, events_per_session,
            # NOT MATCHED (insert)
            fetch_date,
            int(data.get("reach", 0)),
            int(data.get("profile_views", 0)),
            int(data.get("accounts_engaged", 0)),
            int(data.get("website_clicks", 0)),
            int(data.get("total_interactions", 0)),
            created_at,
            sessions, new_users, engagement_rate, avg_sess_dur, events_per_session,
        )
        cursor.execute(sql_ga, params_ga)
        conn.commit()
    finally:
        conn.close()
