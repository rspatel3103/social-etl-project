# social_etl/extractors/google_analytics.py
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Iterable, List

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension,
    FilterExpression, Filter, GetMetadataRequest
)

def _resolve_fetch_date() -> str:
    v = (os.getenv("GA_FETCH_DATE") or "yesterday").strip().lower()
    now = datetime.now(timezone.utc).astimezone()
    if v == "today": return now.strftime("%Y-%m-%d")
    if v == "yesterday": return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return v  # YYYY-MM-DD

def _to_float(s: str) -> float:
    try: return float(s.replace(",", ""))
    except: return 0.0

def _to_int(s: str) -> int:
    try: return int(float(s.replace(",", "")))
    except: return 0

def _assert_supported_fields(client: BetaAnalyticsDataClient, property_id: str,
                             metrics: List[str], dimensions: List[str]) -> None:
    meta = client.get_metadata(GetMetadataRequest(name=f"properties/{property_id}/metadata"))
    mset = {m.api_name for m in meta.metrics}
    dset = {d.api_name for d in meta.dimensions}
    missing_m = [m for m in metrics if m not in mset]
    missing_d = [d for d in dimensions if d not in dset]
    if missing_m or missing_d:
        raise ValueError(f"Unsupported GA4 fields — metrics: {missing_m}, dimensions: {missing_d}")

def _fetch_core_metrics(client: BetaAnalyticsDataClient, property_id: str, day: str) -> Dict[str, float | int]:
    metrics = [
        Metric(name="totalUsers"),            # reach
        Metric(name="newUsers"),
        Metric(name="sessions"),
        Metric(name="engagedSessions"),       # accounts_engaged
        Metric(name="engagementRate"),
        Metric(name="averageSessionDuration"),
        Metric(name="screenPageViews"),       # profile_views
        Metric(name="eventCount"),            # total_interactions
        Metric(name="eventsPerSession"),
    ]
    _assert_supported_fields(client, property_id, [m.name for m in metrics], [])

    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        dimensions=[],
        metrics=metrics,
        limit=1,
    )
    res = client.run_report(req)
    if not res.rows:
        return {}

    out: Dict[str, float | int] = {}
    row = res.rows[0].metric_values
    for i, m in enumerate(metrics):
        name, val = m.name, row[i].value
        if name in {"engagementRate", "averageSessionDuration", "eventsPerSession"}:
            out[name] = _to_float(val)
        else:
            num = _to_float(val)
            out[name] = int(num) if num.is_integer() else num
    return out

def _count_outbound_clicks(client: BetaAnalyticsDataClient, property_id: str, day: str,
                           event_name: str, outbound_only: bool, ignore_domains_csv: str | None) -> int:
    dims = [Dimension(name="eventName"), Dimension(name="linkDomain")]
    _assert_supported_fields(client, property_id, ["eventCount"], [d.name for d in dims])

    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        dimensions=dims,
        metrics=[Metric(name="eventCount")],
        dimension_filter=FilterExpression(filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(value=event_name, match_type=Filter.StringFilter.MatchType.EXACT),
        )),
        limit=100000,
    )
    res = client.run_report(req)

    ignore = {d.strip().lower() for d in (ignore_domains_csv or "").split(",") if d.strip()}
    total = 0
    for r in res.rows:
        ev = r.dimension_values[0].value or ""
        dom = (r.dimension_values[1].value or "").lower()
        cnt = _to_int(r.metric_values[0].value)
        if ev != event_name: continue
        if outbound_only and not dom: continue
        if dom and dom in ignore: continue
        total += cnt
    return total

def fetch_insights() -> Dict[str, Any]:
    prop = os.getenv("GA4_PROPERTY_ID")
    if not prop or not prop.strip().isdigit():
        raise EnvironmentError("GA4_PROPERTY_ID must be numeric.")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not set.")

    day = _resolve_fetch_date()
    client = BetaAnalyticsDataClient()

    core = _fetch_core_metrics(client, prop.strip(), day)

    ev = (os.getenv("GA_WEBSITE_CLICKS_EVENT") or "click").strip()
    outbound_only = os.getenv("GA_WEBSITE_CLICKS_OUTBOUND_ONLY", "true").lower() in {"1","true","yes"}
    ignore_csv = os.getenv("GA_WEBSITE_CLICKS_IGNORE_DOMAINS")
    website_clicks = _count_outbound_clicks(client, prop.strip(), day, ev, outbound_only, ignore_csv)

    return {
        # 5 standard
        "reach": int(core.get("totalUsers", 0)),
        "profile_views": int(core.get("screenPageViews", 0)),
        "accounts_engaged": int(core.get("engagedSessions", 0)),
        "website_clicks": int(website_clicks),
        "total_interactions": int(core.get("eventCount", 0)),
        # GA extras (final set)
        "sessions": int(core.get("sessions", 0)),
        "new_users": int(core.get("newUsers", 0)),
        "engagement_rate": float(core.get("engagementRate", 0.0)),
        "avg_session_duration_sec": float(core.get("averageSessionDuration", 0.0)),
        "events_per_session": float(core.get("eventsPerSession", 0.0)),
        # no key_events anymore
    }
