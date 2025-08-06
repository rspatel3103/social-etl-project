"""
Entry point for the unified social media ETL pipeline.

Running this script will load environment variables from a ``.env``
file, iterate over the supported platforms, extract their daily
insights, transform the raw data into a standard format and load the
results into a SQL Server database. The script also persists a JSON
snapshot of the transformed data for each platform under the
``etl_snapshots`` directory. These snapshots serve as an audit trail
and can assist in debugging.

To add a new platform, update the ``PLATFORMS`` list below with the
appropriate extractor and transformer modules. Each element must be a
tuple consisting of the platform name (used for logging, table
naming and snapshot file prefixes), the extractor module and the
transformer module.

Example
-------
To run the ETL process for all platforms defined in ``PLATFORMS``,
execute this module as a script:

``python -m social_etl.main``
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Tuple, List

from .utils.env_loader import load_env
from .loaders.sql_loader import load_to_sql


def save_json_snapshot(data: Dict[str, Any], platform: str, folder: str = "etl_snapshots") -> str:
    """Persist a JSON snapshot of the transformed data.

    Parameters
    ----------
    data : dict
        The transformed insights data to persist.
    platform : str
        The platform name used as a prefix for the snapshot file.
    folder : str, optional
        Directory in which to store snapshots. Created if it does not
        exist.

    Returns
    -------
    str
        The path to the saved JSON file.
    """
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{platform}_snapshot_{timestamp}.json"
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


# Define the platforms to process. Each tuple consists of:
# (platform_name, extractor_module_path, transformer_module_path)
# The module paths are relative to the ``social_etl`` package.
PLATFORMS: List[Tuple[str, str, str]] = [
    ("instagram", "social_etl.extractors.instagram", "social_etl.transformers.instagram"),
    ("linkedin", "social_etl.extractors.linkedin", "social_etl.transformers.linkedin"),
    ("facebook", "social_etl.extractors.facebook", "social_etl.transformers.facebook"),
    ("x", "social_etl.extractors.x_platform", "social_etl.transformers.x_platform"),
]


def run_platform(platform_name: str, extractor_module: str, transformer_module: str) -> None:
    """Run the ETL process for a single platform.

    Parameters
    ----------
    platform_name : str
        A short identifier for the platform (used in table names and
        snapshot filenames).
    extractor_module : str
        The import path for the extractor module.
    transformer_module : str
        The import path for the transformer module.
    """
    # Dynamically import the extractor and transformer modules. This
    # approach allows new platforms to be added simply by adding a new
    # tuple to the PLATFORMS list.
    extractor = import_module(extractor_module)
    transformer = import_module(transformer_module)

    print(f"📦 Extracting {platform_name} insights...")
    raw = extractor.fetch_insights()
    print(f"📊 Raw data for {platform_name}: {raw}")

    print(f"🔧 Transforming {platform_name} insights...")
    clean = transformer.transform_insights(raw)
    print(f"✅ Transformed data for {platform_name}: {clean}")

    snapshot_path = save_json_snapshot(clean, platform=platform_name)
    print(f"🗂️  Snapshot for {platform_name} saved at: {snapshot_path}")

    print(f"⬆️  Loading {platform_name} data into SQL...")
    load_to_sql(clean, platform=platform_name)
    print(f"✅ {platform_name.capitalize()} data loaded successfully.\n")


def main() -> None:
    """Main entry point for running the ETL across all platforms."""
    # Load environment variables before any API calls
    load_env()

    for platform_name, extractor_path, transformer_path in PLATFORMS:
        try:
            run_platform(platform_name, extractor_path, transformer_path)
        except Exception as exc:
            # Log the error and continue with the next platform
            print(f"❌ ETL failed for {platform_name}: {exc}")
            # Append the error to a log file with a timestamp
            with open("etl_log.txt", "a", encoding="utf-8") as log:
                log.write(
                    f"{datetime.now()} - ❌ ETL failed for {platform_name} - {exc}\n"
                )


if __name__ == "__main__":
    main()
