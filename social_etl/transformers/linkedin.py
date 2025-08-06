"""
LinkedIn transformer.

LinkedIn’s API might return metrics under different names than those
used by this project. This transformer normalises the raw data
returned by the LinkedIn extractor into the standard format. At
present the extractor returns a dictionary with keys already matching
the expected ones, so the transformer simply fills missing keys with
zeros. If you update the extractor to return LinkedIn specific
names, map them here accordingly.
"""

from __future__ import annotations

from typing import Dict, Any


def transform_insights(raw_data: Dict[str, Any]) -> Dict[str, int]:
    """Normalise raw LinkedIn insights.

    This implementation simply ensures all expected keys are present.

    Parameters
    ----------
    raw_data : dict
        Raw dictionary returned by :func:`social_etl.extractors.linkedin.fetch_insights`.

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
