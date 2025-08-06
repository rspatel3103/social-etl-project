"""
Facebook Page insights extractor.

This module fetches daily insights for a Facebook Page via the
Facebook Graph API. In order to use this extractor you need a Page
ID and an access token with the appropriate permissions
(``pages_read_engagement`` and ``pages_read_user_content``). Store
these values in the ``FACEBOOK_PAGE_ID`` and ``FACEBOOK_ACCESS_TOKEN``
environment variables or in your ``.env`` file.

The Graph API exposes a large number of metrics. For consistency
across platforms, this extractor focuses on a small set that map
directly to the project’s standard metric names. If additional
metrics become important for your use case, you can extend the
returned dictionary accordingly and add new columns to the SQL
schema.

Note that the current implementation is intentionally conservative:
if no credentials are provided the extractor returns zeros for all
metrics and logs a warning. Replace the TODO sections with actual
requests to the Facebook Graph API once you have acquired the
necessary credentials.
"""

from __future__ import annotations

import os
from typing import Dict, Any


def fetch_insights() -> Dict[str, Any]:
    """Fetch daily insights for a Facebook Page.

    Returns a dictionary of the standard metrics with integer values. On
    error or missing credentials, all metrics default to zero. See the
    module docstring for guidance on enabling real API integration.

    Returns
    -------
    dict
        Mapping of ``reach``, ``profile_views``, ``accounts_engaged``,
        ``website_clicks`` and ``total_interactions`` to integer values.
    """
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    token = os.getenv("FACEBOOK_ACCESS_TOKEN")
    if not page_id or not token:
        print("⚠️  FACEBOOK_PAGE_ID or FACEBOOK_ACCESS_TOKEN not set. Returning zero values.")
        return {
            "reach": 0,
            "profile_views": 0,
            "accounts_engaged": 0,
            "website_clicks": 0,
            "total_interactions": 0,
        }

    # TODO: call Facebook Graph API /{page-id}/insights with appropriate
    # metrics. See https://developers.facebook.com/docs/graph-api/reference/page/insights/
    # The result should be parsed and returned in the format below. For
    # example:
    # metrics = {
    #     "reach": get_value(...),
    #     "profile_views": get_value(...),
    #     ...
    # }

    # Placeholder values until real implementation is provided
    return {
        "reach": 0,
        "profile_views": 0,
        "accounts_engaged": 0,
        "website_clicks": 0,
        "total_interactions": 0,
    }
