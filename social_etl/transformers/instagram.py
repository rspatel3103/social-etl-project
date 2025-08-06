"""
Instagram transformer.

The Instagram extractor already produces a dictionary keyed by the
standard metric names used across the project. This transformer is
therefore quite simple: it ensures that all expected keys are
present and fills in zeros where necessary. More complex logic
(renaming or aggregating metrics) could be added here in the future
without affecting the extractor or the SQL loader.
"""

from __future__ import annotations

from typing import Dict, Any


def transform_insights(raw_data: Dict[str, Any]) -> Dict[str, int]:
    """Normalise raw Instagram insights.

    Parameters
    ----------
    raw_data : dict
        Raw dictionary returned by :func:`social_etl.extractors.instagram.fetch_insights`.

    Returns
    -------
    dict
        Normalised dictionary containing all expected metric keys.
    """
    # Define the standard metrics and supply a default of zero for
    # missing keys
    keys = [
        "reach",
        "profile_views",
        "accounts_engaged",
        "website_clicks",
        "total_interactions",
    ]
    return {k: int(raw_data.get(k, 0) or 0) for k in keys}
