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

NOTE (2025-12): For the Google Analytics table **GA_insights_daily** only,
we store **one column per GA4 metric** (discovered from the GA4 Metadata API),
and we add new columns automatically when new metrics appear.
Other platform tables are NOT changed.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

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


def _infer_sql_type(value: Any) -> str:
    """Infer a SQL Server type for a metric column."""
    if value is None:
        return "FLOAT"
    if isinstance(value, bool):
        return "INT"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "FLOAT"
    return "NVARCHAR(MAX)"


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


def _ensure_columns(cursor: pyodbc.Cursor, table_name: str, cols: Dict[str, str]) -> None:
    """Add missing columns (nullable)."""
    for col, typ in cols.items():
        if col == "fetch_date":
            continue
        if not _column_exists(cursor, table_name, col):
            cursor.execute(f"ALTER TABLE [{table_name}] ADD [{col}] {typ} NULL;")


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
    GA_insights_daily: base table (fetch_date, created_at); metric columns are added dynamically.
    """
    safe_table = f"[{table_name}]"

    if not _table_exists(cursor, table_name):
        if _is_ga_table(table_name):
            # GA table stores one column per GA metric (created dynamically).
            cursor.execute(f"""
                CREATE TABLE {safe_table} (
                    fetch_date DATE PRIMARY KEY,
                    created_at DATETIME
                )
            """)
        else:
            # Non-GA platforms: base 5 standard columns
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
        return

    # Existing tables: GA columns are added dynamically in load_to_sql.


# ------------------------------ Upsert ------------------------------ #

def load_to_sql(data: Dict[str, Any], platform: str) -> None:
    """Load transformed data into the SQL Server table for a platform."""
    table_name = f"{platform}_insights_daily"
    is_ga = _is_ga_table(table_name)

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        ensure_table_exists(cursor, table_name)

        # Respect the transformer-provided fetch_date when present (e.g., GA pulling yesterday).
        fetch_date = data.get("fetch_date") or datetime.today().date()
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

        # --- GA table: dynamic metric columns (one column per metric) ---

        # Ensure any missing columns exist before the MERGE.
        metric_cols: Dict[str, str] = {}
        for k, v in data.items():
            if k in {"fetch_date", "created_at"}:
                continue
            metric_cols[k] = _infer_sql_type(v)
        _ensure_columns(cursor, table_name, metric_cols)

        # Build dynamic MERGE.
        cols = sorted(metric_cols.keys())
        update_set = ",\n                ".join([f"[{c}] = ?" for c in cols] + ["created_at = ?"])
        insert_cols = ", ".join(["fetch_date"] + [f"[{c}]" for c in cols] + ["created_at"])
        insert_vals = ", ".join(["?"] * (1 + len(cols) + 1))

        sql_ga = f"""
            MERGE {safe_table} AS target
            USING (SELECT ? AS fetch_date) AS source
            ON target.fetch_date = source.fetch_date
            WHEN MATCHED THEN UPDATE SET
                {update_set}
            WHEN NOT MATCHED THEN
                INSERT ({insert_cols})
                VALUES ({insert_vals});
        """

        # Params order:
        #   1) source.fetch_date
        #   2) UPDATE values (cols...) + created_at
        #   3) INSERT values: fetch_date + cols... + created_at
        update_params = [data.get(c) for c in cols] + [created_at]
        insert_params = [fetch_date] + [data.get(c) for c in cols] + [created_at]
        params_ga = tuple([fetch_date] + update_params + insert_params)

        cursor.execute(sql_ga, params_ga)
        conn.commit()
    finally:
        conn.close()
