"""
Instagram extractor.

This module encapsulates all logic required to fetch insight metrics
from the Instagram Graph API. The extractor reads the account ID and
access token from environment variables (see ``INSTAGRAM_ACCOUNT_ID``
and ``INSTAGRAM_ACCESS_TOKEN``) so that secrets are not hard coded in
the source. For more details on the available metrics, see the
Instagram Graph API documentation for ``/{ig-id}/insights``.

The current implementation retrieves a limited set of metrics that are
available for an Instagram business account:

* ``reach`` – daily reach
* ``profile_views`` – total profile views for the day
* ``accounts_engaged`` – total engaged accounts
* ``website_clicks`` – number of website clicks
* ``total_interactions`` – combined count of likes, comments and
  other interactions

If you wish to add or remove metrics, update the ``PROFILE_METRICS``
list accordingly and adjust the transformer if necessary. See
``transformers.instagram`` for an example of how to normalise raw
results.
"""

from __future__ import annotations
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Dict, Any

import requests
from helpers import get_access_token


# Read account ID and token from environment
ACCOUNT_ID = os.getenv("INSTAGRAM_APP_ID")
ACCESS_TOKEN = get_access_token("instagram")

# Base URL for the insights endpoint
INSIGHTS_BASE = f"https://graph.facebook.com/v19.0/{ACCOUNT_ID}/insights"

# Metrics grouped by API requirements
REACH_METRIC = "reach"  # period=day
PROFILE_METRICS = [
    "profile_views",
    "accounts_engaged",
    "website_clicks",
    "total_interactions"
]  # require period=day + metric_type=total_value


def fetch_insights() -> Dict[str, Any]:
    """Fetch daily insights from the Instagram Graph API.

    Returns
    -------
    dict
        A mapping of metric names to integer values. Missing metrics
        default to zero.

    Raises
    ------
    Exception
        If the HTTP request fails or the JSON response does not
        contain the expected data. The caller is responsible for
        handling these exceptions (e.g. by logging and continuing
        with other platforms).
    """
    if not ACCOUNT_ID or not ACCESS_TOKEN:
        raise EnvironmentError(
            "Instagram credentials are not set. Define INSTAGRAM_ACCOUNT_ID "
            "and INSTAGRAM_ACCESS_TOKEN in your environment or .env file."
        )

    all_metrics: Dict[str, Any] = {
        "reach": 0,
        "profile_views": 0,
        "accounts_engaged": 0,
        "website_clicks": 0,
        "total_interactions": 0,
    }

    # 1. Reach (period=day)
    reach_params = {
        "metric": REACH_METRIC,
        "period": "day",
        "access_token": ACCESS_TOKEN,
    }
    reach_resp = requests.get(INSIGHTS_BASE, params=reach_params, timeout=30)
    reach_resp.raise_for_status()
    for item in reach_resp.json().get("data", []):
        # Use the value for today
        all_metrics[item["name"]] = item.get("values", [{}])[0].get("value", 0)

    # 2. Profile-level metrics (metric_type=total_value + period=day)
    profile_params = {
        "metric": ",".join(PROFILE_METRICS),
        "metric_type": "total_value",
        "period": "day",
        "access_token": ACCESS_TOKEN,
    }
    profile_resp = requests.get(INSIGHTS_BASE, params=profile_params, timeout=30)
    profile_resp.raise_for_status()
    for item in profile_resp.json().get("data", []):
        # Many metrics return their value under the key 'total_value'
        all_metrics[item["name"]] = item.get("total_value", {}).get("value", 0)

    return all_metrics
