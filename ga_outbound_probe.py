# ga_outbound_probe.py
import os
from social_etl.utils.env_loader import load_env
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

load_env()  # <-- pulls .env into this process

prop = os.getenv("GA4_PROPERTY_ID")
print("GA4_PROPERTY_ID raw:", repr(prop))
assert prop and prop.strip().isdigit(), "GA4_PROPERTY_ID must be numeric"
prop = prop.strip()
day = os.getenv("GA_FETCH_DATE", "yesterday")

client = BetaAnalyticsDataClient()
req = RunReportRequest(
    property=f"properties/{prop}",
    date_ranges=[DateRange(start_date=day, end_date=day)],
    dimensions=[Dimension(name="eventName"), Dimension(name="isOutbound"), Dimension(name="linkDomain")],
    metrics=[Metric(name="eventCount")],
)
resp = client.run_report(req)
for r in resp.rows or []:
    print(tuple(d.value for d in r.dimension_values), "->", r.metric_values[0].value)
