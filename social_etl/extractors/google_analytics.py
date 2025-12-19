# social_etl/extractors/google_analytics.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Iterable, Optional

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension,
    FilterExpression, Filter, GetMetadataRequest,
)

# GA Data API allows up to 10 metrics per report request.
_MAX_METRICS_PER_REQUEST = 10


def _resolve_fetch_date() -> str:
    v = (os.getenv("GA_FETCH_DATE") or "yesterday").strip().lower()
    now = datetime.now(timezone.utc).astimezone()
    if v == "today":
        return now.strftime("%Y-%m-%d")
    if v == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return v  # expected YYYY-MM-DD


def _to_float(s: str) -> float:
    try:
        return float((s or "0").replace(",", ""))
    except Exception:
        return 0.0


def _to_int(s: str) -> int:
    try:
        return int(float((s or "0").replace(",", "")))
    except Exception:
        return 0


def _assert_supported_fields(
    client: BetaAnalyticsDataClient,
    property_id: str,
    metrics: List[str],
    dimensions: List[str],
) -> None:
    meta = client.get_metadata(GetMetadataRequest(name=f"properties/{property_id}/metadata"))
    mset = {m.api_name for m in meta.metrics}
    dset = {d.api_name for d in meta.dimensions}
    missing_m = [m for m in metrics if m not in mset]
    missing_d = [d for d in dimensions if d not in dset]
    if missing_m or missing_d:
        raise ValueError(f"Unsupported GA4 fields — metrics: {missing_m}, dimensions: {missing_d}")


def _metric_type_name(metric_meta: Any) -> str:
    t = getattr(metric_meta, "type", None)
    if hasattr(t, "name") and t.name:
        return str(t.name)
    if isinstance(t, str):
        return t
    return ""


def _coerce_metric_value(metric_type: str, value_str: str) -> int | float:
    v = _to_float(value_str)
    if metric_type == "TYPE_INTEGER":
        return int(v)
    if float(v).is_integer():
        return int(v)
    return float(v)


def _get_all_metric_metas(client: BetaAnalyticsDataClient, property_id: str) -> List[Any]:
    meta = client.get_metadata(GetMetadataRequest(name=f"properties/{property_id}/metadata"))
    return list(meta.metrics)


def _run_report_metrics_only(
    client: BetaAnalyticsDataClient,
    property_id: str,
    day: str,
    metric_names: List[str],
) -> Dict[str, str]:
    """Run a GA report with no dimensions and return metric values as strings."""
    _assert_supported_fields(client, property_id, metric_names, [])
    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        metrics=[Metric(name=m) for m in metric_names],
    )
    res = client.run_report(req)
    if not res.rows:
        return {m: "0" for m in metric_names}
    row_vals = res.rows[0].metric_values
    out: Dict[str, str] = {}
    for i, m in enumerate(metric_names):
        out[m] = row_vals[i].value
    return out


def _fetch_all_metrics(
    client: BetaAnalyticsDataClient,
    property_id: str,
    day: str,
) -> Tuple[Dict[str, int | float], List[str]]:
    """Fetch *all* available GA4 metrics for a property for a single day.

    Returns:
      (metrics_dict, failed_metrics)
    """
    metas = _get_all_metric_metas(client, property_id)
    names = [m.api_name for m in metas if getattr(m, "api_name", None)]
    type_map = {m.api_name: _metric_type_name(m) for m in metas if getattr(m, "api_name", None)}

    def chunks(xs: List[str], n: int) -> Iterable[List[str]]:
        for i in range(0, len(xs), n):
            yield xs[i : i + n]

    results: Dict[str, int | float] = {}
    failed: List[str] = []

    # Some metric combinations can be incompatible. We try batching first and
    # recursively split batches on failure.
    def fetch_batch(batch: List[str]) -> None:
        nonlocal results, failed
        try:
            raw = _run_report_metrics_only(client, property_id, day, batch)
            for k, v in raw.items():
                results[k] = _coerce_metric_value(type_map.get(k, ""), v)
        except Exception:
            if len(batch) == 1:
                failed.append(batch[0])
                return
            mid = max(1, len(batch) // 2)
            fetch_batch(batch[:mid])
            fetch_batch(batch[mid:])

    for batch in chunks(names, _MAX_METRICS_PER_REQUEST):
        fetch_batch(batch)

    return results, failed


def _count_outbound_clicks(
    client: BetaAnalyticsDataClient,
    property_id: str,
    day: str,
    event_name: str,
    outbound_only: bool,
    ignore_domains_csv: Optional[str],
) -> int:
    dims = [Dimension(name="eventName"), Dimension(name="linkDomain")]
    _assert_supported_fields(client, property_id, ["eventCount"], [d.name for d in dims])

    req = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=day, end_date=day)],
        dimensions=dims,
        metrics=[Metric(name="eventCount")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    value=event_name,
                    match_type=Filter.StringFilter.MatchType.EXACT,
                ),
            )
        ),
        limit=100000,
    )
    res = client.run_report(req)

    ignore = {d.strip().lower() for d in (ignore_domains_csv or "").split(",") if d.strip()}
    total = 0
    for r in res.rows:
        ev = r.dimension_values[0].value or ""
        dom = (r.dimension_values[1].value or "").lower()
        cnt = _to_int(r.metric_values[0].value)
        if ev != event_name:
            continue
        if outbound_only and not dom:
            continue
        if dom and dom in ignore:
            continue
        total += cnt
    return total


def fetch_insights() -> Dict[str, Any]:
    """Fetch GA4 daily metrics.

    Environment:
      - GA4_PROPERTY_ID (required): numeric GA4 property id
      - GOOGLE_APPLICATION_CREDENTIALS (required): path to service account json
      - GA_FETCH_DATE: 'today', 'yesterday', or YYYY-MM-DD (default: yesterday)

      Website clicks (optional):
      - GA_WEBSITE_CLICKS_EVENT (default: 'click')
      - GA_WEBSITE_CLICKS_OUTBOUND_ONLY (default: true)
      - GA_WEBSITE_CLICKS_IGNORE_DOMAINS: comma-separated domains to ignore

    Output:
      - fetch_date: YYYY-MM-DD used for the report (intended to be the SQL primary key)
      - website_clicks: outbound click event count (optional, derived)
      - ga_metrics: dict of *all* GA metrics for the day (api_name -> value)
    """
    prop = os.getenv("GA4_PROPERTY_ID")
    if not prop or not prop.strip().isdigit():
        raise EnvironmentError("GA4_PROPERTY_ID must be numeric.")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not set.")

    day = _resolve_fetch_date()
    client = BetaAnalyticsDataClient()

    all_metrics, _failed = _fetch_all_metrics(client, prop.strip(), day)

    ev = (os.getenv("GA_WEBSITE_CLICKS_EVENT") or "click").strip()
    outbound_only = os.getenv("GA_WEBSITE_CLICKS_OUTBOUND_ONLY", "true").lower() in {"1", "true", "yes"}
    ignore_csv = os.getenv("GA_WEBSITE_CLICKS_IGNORE_DOMAINS")
    website_clicks = _count_outbound_clicks(client, prop.strip(), day, ev, outbound_only, ignore_csv)

    return {
        "fetch_date": day,
        "website_clicks": int(website_clicks),
        "ga_metrics": all_metrics,
    }
