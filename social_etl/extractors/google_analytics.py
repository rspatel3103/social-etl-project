# social_etl/extractors/google_analytics.py
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

def _resolve_fetch_date() -> str:
    v = (os.getenv("GA_FETCH_DATE") or "yesterday").strip().lower()
    now = datetime.now(timezone.utc).astimezone()
    if v == "today": return now.strftime("%Y-%m-%d")
    if v == "yesterday": return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    datetime.strptime(v, "%Y-%m-%d"); return v

def _to_int(x: str) -> int:
    try: return int(float(x))
    except: return 0

def _fetch_totals(client: BetaAnalyticsDataClient, prop: str, day: str) -> Dict[str,int]:
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        metrics=[Metric(name="totalUsers"), Metric(name="screenPageViews"),
                 Metric(name="engagedSessions"), Metric(name="eventCount")],
    )
    resp = client.run_report(req)
    if not resp.rows:
        return {"totalUsers":0,"screenPageViews":0,"engagedSessions":0,"eventCount":0}
    m = resp.rows[0].metric_values
    return {"totalUsers":_to_int(m[0].value), "screenPageViews":_to_int(m[1].value),
            "engagedSessions":_to_int(m[2].value), "eventCount":_to_int(m[3].value)}

def _count_outbound_clicks(client: BetaAnalyticsDataClient, prop: str, day: str,
                           event_name: str, outbound_only: bool, ignore_csv: str|None) -> int:
    """
    Count clicks client-side using GA4 dimensions:
      - eventName == <event_name> (e.g., 'click')
      - outbound == 'true' (when outbound_only=True)
      - linkDomain NOT IN ignore list (optional)
    """
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        dimensions=[Dimension(name="eventName"), Dimension(name="outbound"), Dimension(name="linkDomain")],
        metrics=[Metric(name="eventCount")],
    )
    resp = client.run_report(req)
    if not resp.rows:
        return 0

    ignore = set(d.strip().lower() for d in (ignore_csv or "").split(",") if d and d.strip())
    total = 0
    for r in resp.rows:
        ev  = (r.dimension_values[0].value or "")
        out = (r.dimension_values[1].value or "").lower()  # 'true' or 'false'
        dom = (r.dimension_values[2].value or "").lower()
        if ev != event_name:
            continue
        if outbound_only and out != "true":
            continue
        if dom and dom in ignore:
            continue
        total += _to_int(r.metric_values[0].value)
    return total

def fetch_insights() -> Dict[str, Any]:
    prop = os.getenv("GA4_PROPERTY_ID")
    if not prop or not prop.strip().isdigit():
        raise EnvironmentError("GA4_PROPERTY_ID must be your numeric GA4 Property ID.")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS must point to your service account JSON.")
    prop = prop.strip()

    day = _resolve_fetch_date()
    client = BetaAnalyticsDataClient()
    totals = _fetch_totals(client, prop, day)

    website_clicks = 0
    ev = (os.getenv("GA_WEBSITE_CLICKS_EVENT") or "").strip()  # e.g., 'click' for Enhanced Measurement
    if ev:
        outbound_only = os.getenv("GA_WEBSITE_CLICKS_OUTBOUND_ONLY","false").lower() in {"1","true","yes"}
        ignore_csv = os.getenv("GA_WEBSITE_CLICKS_IGNORE_DOMAINS")
        website_clicks = _count_outbound_clicks(client, prop, day, ev, outbound_only, ignore_csv)

    return {
        "reach": totals["totalUsers"],
        "profile_views": totals["screenPageViews"],
        "accounts_engaged": totals["engagedSessions"],
        "website_clicks": website_clicks,
        "total_interactions": totals["eventCount"],
    }
