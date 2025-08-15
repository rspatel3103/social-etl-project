import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from helpers import get_access_token

def fetch_insights() -> Dict[str, Any]:
    page_id = os.getenv("FACEBOOK_APP_ID")
    access_token = get_access_token("facebook")

    if not page_id or not access_token:
        print("⚠️ FACEBOOK_PAGE_ID or FACEBOOK_ACCESS_TOKEN not set. Returning zeros.")
        return {
            "reach": 0,
            "profile_views": 0,
            "accounts_engaged": 0,
            "website_clicks": 0,
            "total_interactions": 0
        }

    metrics_url = f"https://graph.facebook.com/v19.0/{page_id}/insights"
    metrics_params = {
        "access_token": access_token,
        "metric": "page_impressions_unique,page_views_total,page_post_engagements",
        "period": "day"
    }

    page_metrics = {
        "reach": 0,
        "profile_views": 0,
        "total_interactions": 0
    }

    try:
        insights_resp = requests.get(metrics_url, params=metrics_params, timeout=15)
        insights_resp.raise_for_status()
        insights_data = insights_resp.json().get("data", [])

        today = datetime.utcnow().date() - timedelta(days=1)


        for metric in insights_data:
            name = metric.get("name")
            values = metric.get("values", [])

            for value_obj in values:
                end_time = value_obj.get("end_time")
                if not end_time:
                    continue

                metric_date = datetime.fromisoformat(end_time.replace("Z", "+00:00")).date()
                if metric_date == today:
                    value = value_obj.get("value", 0)

                    if name == "page_impressions_unique":
                        page_metrics["reach"] = int(value)
                    elif name == "page_views_total":
                        page_metrics["profile_views"] = int(value)
                    elif name == "page_post_engagements":
                        page_metrics["total_interactions"] = int(value)

    except Exception as e:
        print(f"⚠️ Failed to fetch insights metrics: {e}")

    accounts_engaged = 1 if page_metrics["total_interactions"] > 0 else 0

    return {
        "reach": page_metrics["reach"],
        "profile_views": page_metrics["profile_views"],
        "accounts_engaged": accounts_engaged,
        "website_clicks": 0,
        "total_interactions": page_metrics["total_interactions"]
    }
