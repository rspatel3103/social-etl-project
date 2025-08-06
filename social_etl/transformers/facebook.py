"""
Facebook transformer.

The Facebook extractor is expected to return a dictionary keyed by the
standard metric names used across the project. This transformer
ensures that all expected keys are present and converts any missing
values to zeros. If you choose to return different keys from the
extractor (for example, mapping ``page_impressions`` to ``reach``),
you should implement that mapping here.
"""

from __future__ import annotations

from typing import Dict, Any


def transform_insights(raw_data: Dict[str, Any]) -> Dict[str, int]:
    """Normalise raw Facebook insights.

    Parameters
    ----------
    raw_data : dict
        Raw dictionary returned by :func:`social_etl.extractors.facebook.fetch_insights`.

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
