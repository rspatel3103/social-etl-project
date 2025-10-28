"""
Google Analytics (GA4) transformer.

Contract:
  - Exposes transform_insights(raw: dict) -> dict
  - Normalizes to the standard keys expected by the SQL loader:
      reach, profile_views, accounts_engaged, website_clicks, total_interactions

Note:
  - This transformer is intentionally minimal to match the pattern used by other platforms
    in your project (e.g., Instagram): it validates keys and coerces to int.
"""

from __future__ import annotations
from typing import Dict, Any

def transform_insights(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw_data, dict):
        raise ValueError("GA transformer expected a dict payload.")

    keys = [
        "reach",
        "profile_views",
        "accounts_engaged",
        "website_clicks",
        "total_interactions",
    ]
    # Coerce all values to int, defaulting missing metrics to 0
    return {k: int(raw_data.get(k, 0) or 0) for k in keys}
