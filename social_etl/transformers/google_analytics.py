# social_etl/transformers/google_analytics.py
from __future__ import annotations

import re
from typing import Dict, Any


_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z_]")
_MULTI_UNDERSCORE_RE = re.compile(r"_+")


def _sanitize_column(name: str) -> str:
    """Convert a GA4 metric API name into a SQL-safe column name.

    Examples:
      keyEvents:purchase -> keyEvents_purchase
      1DayActiveUsers -> m_1DayActiveUsers
    """
    n = (name or "").strip()
    n = _NON_ALNUM_RE.sub("_", n)
    n = _MULTI_UNDERSCORE_RE.sub("_", n).strip("_")
    if not n:
        return "m_unknown"
    if n[0].isdigit():
        n = f"m_{n}"
    # SQL Server max identifier length is 128; keep some buffer.
    return n[:120]


def transform_insights(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten GA4 metrics into a column-per-metric payload for SQL Server.

    Expected raw keys (from extractor):
      - fetch_date: YYYY-MM-DD
      - website_clicks: int
      - ga_metrics: dict(api_name -> numeric)
    """
    out: Dict[str, Any] = {}

    # Primary key date used by loader.
    if raw.get("fetch_date"):
        out["fetch_date"] = raw["fetch_date"]

    # Keep this derived value as its own column.
    if "website_clicks" in raw:
        try:
            out["website_clicks"] = int(raw.get("website_clicks") or 0)
        except Exception:
            out["website_clicks"] = 0

    metrics = raw.get("ga_metrics") or {}
    if isinstance(metrics, dict):
        for api_name, value in metrics.items():
            col = _sanitize_column(str(api_name))
            # Avoid collisions: if two names sanitize to same column, suffix.
            if col in out:
                i = 2
                while f"{col}_{i}" in out:
                    i += 1
                col = f"{col}_{i}"
            out[col] = value

    return out
