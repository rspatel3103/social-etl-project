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
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any

import pyodbc


def _get_connection() -> pyodbc.Connection:
    """Create a new connection to the SQL Server using ``SQL_CONN_STR``.

    Raises
    ------
    EnvironmentError
        If ``SQL_CONN_STR`` is not set.
    """
    conn_str = os.getenv("SQL_CONN_STR")
    if not conn_str:
        raise EnvironmentError(
            "SQL_CONN_STR is not set. Define it in your environment or .env file."
        )
    return pyodbc.connect(conn_str)


def ensure_table_exists(cursor: pyodbc.Cursor, table_name: str) -> None:
    """Ensure the target table exists for the given platform.

    If the table does not exist it will be created with the standard
    columns: ``fetch_date`` (DATE PRIMARY KEY), ``reach``,
    ``profile_views``, ``accounts_engaged``, ``website_clicks`` and
    ``total_interactions`` (all INT). This function is idempotent; it
    can be called repeatedly without side effects.

    Parameters
    ----------
    cursor : pyodbc.Cursor
        A cursor connected to the target database.
    table_name : str
        Name of the table (without schema) to ensure.
    """
    # Escape the table name to avoid SQL injection. Because the
    # identifier comes from our code (platform names), we trust it
    # implicitly but still wrap it in brackets as a best practice.
    safe_table = f"[{table_name}]"
    cursor.execute(f"""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = ?
        )
        BEGIN
            CREATE TABLE {safe_table} (
                fetch_date DATE PRIMARY KEY,
                reach INT,
                profile_views INT,
                accounts_engaged INT,
                website_clicks INT,
                total_interactions INT
            )
        END
    """, table_name)


def load_to_sql(data: Dict[str, Any], platform: str) -> None:
    """Load transformed data into the SQL Server table for a platform.

    This function opens a new database connection, ensures the
    destination table exists and then upserts the provided data for
    the current date. The connection is closed automatically at the
    end of the operation.

    Parameters
    ----------
    data : dict
        The transformed insights dictionary with keys matching the
        standard metrics (``reach``, ``profile_views``,
        ``accounts_engaged``, ``website_clicks``, ``total_interactions``).
    platform : str
        The platform name used to construct the table name. For
        example ``"instagram"`` yields a table ``instagram_insights_daily``.
    """
    table_name = f"{platform}_insights_daily"
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # Ensure table exists before inserting
        ensure_table_exists(cursor, table_name)

        fetch_date = datetime.today().date()

        # Build MERGE statement dynamically with parameter placeholders.
        # Use bracketed table name to avoid reserved words.
        safe_table = f"[{table_name}]"
        sql = f"""
            MERGE {safe_table} AS target
            USING (SELECT ? AS fetch_date) AS source
            ON target.fetch_date = source.fetch_date
            WHEN MATCHED THEN UPDATE SET
                reach = ?, profile_views = ?, accounts_engaged = ?,
                website_clicks = ?, total_interactions = ?
            WHEN NOT MATCHED THEN
                INSERT (fetch_date, reach, profile_views, accounts_engaged, website_clicks, total_interactions)
                VALUES (?, ?, ?, ?, ?, ?);
        """
        params = (
            fetch_date,
            int(data.get("reach", 0)),
            int(data.get("profile_views", 0)),
            int(data.get("accounts_engaged", 0)),
            int(data.get("website_clicks", 0)),
            int(data.get("total_interactions", 0)),
            fetch_date,
            int(data.get("reach", 0)),
            int(data.get("profile_views", 0)),
            int(data.get("accounts_engaged", 0)),
            int(data.get("website_clicks", 0)),
            int(data.get("total_interactions", 0)),
        )
        cursor.execute(sql, params)
        conn.commit()
    finally:
        conn.close()
