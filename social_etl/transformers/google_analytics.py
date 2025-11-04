# social_etl/transformers/google_analytics.py
from __future__ import annotations
from typing import Dict, Any, Optional

def _i(x: Optional[float | int]) -> int:
    try: return int(float(x or 0))
    except: return 0

def _r2(x: Optional[float]) -> float:
    try: return round(float(x or 0.0), 2)
    except: return 0.0

def _r4(x: Optional[float]) -> float:
    try: return round(float(x or 0.0), 4)
    except: return 0.0

def transform_insights(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        # base 5
        "reach":             _i(raw.get("reach")),
        "profile_views":     _i(raw.get("profile_views")),
        "accounts_engaged":  _i(raw.get("accounts_engaged")),
        "website_clicks":    _i(raw.get("website_clicks")),
        "total_interactions":_i(raw.get("total_interactions")),
        # GA extras (final)
        "sessions":                 _i(raw.get("sessions")),
        "new_users":                _i(raw.get("new_users")),
        "engagement_rate":          _r4(raw.get("engagement_rate")),
        "avg_session_duration_sec": _r2(raw.get("avg_session_duration_sec")),
        "events_per_session":       _r4(raw.get("events_per_session")),
    }
