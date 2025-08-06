"""
Twitter (X) transformer.

The extractor for Twitter is currently a stub that returns a
dictionary keyed by the standard metrics. This transformer ensures
that all expected keys are present and converts missing values to
zeros. Should you implement the extractor to return differently
named fields (e.g. ``impressions`` instead of ``reach``), map them
here.
"""

from __future__ import annotations

from typing import Dict, Any


def transform_insights(raw_data: Dict[str, Any]) -> Dict[str, int]:
    """Normalise raw Twitter (X) insights.

    Parameters
    ----------
    raw_data : dict
        Raw dictionary returned by :func:`social_etl.extractors.x_platform.fetch_insights`.

    Returns
    -------
    dict
        Normalised dictionary containing all expected metric keys.
    """
    keys = [
        "reach",
        "profile_views",
        "accounts_engaged",
        "website_clicks",
        "total_interactions",
    ]
    return {k: int(raw_data.get(k, 0) or 0) for k in keys}
