"""
Top level package for the unified social media ETL pipeline.

This package brings together extractors, transformers and loaders for
multiple social platforms and orchestrates them via a simple entry
point (see :mod:`social_etl.main`). By organizing the code into
distinct sub‑packages for each phase of the ETL process and each
supported platform, the repository remains easy to navigate and
extend.

Typical usage from the command line might look like::

    python -m social_etl.main

which will load environment variables from a ``.env`` file, call the
appropriate extractors for each platform, normalise the results via
transformers and write them into a SQL Server database using a shared
schema.

To add a new platform, implement corresponding modules under
``social_etl.extractors`` and ``social_etl.transformers``. Each
extractor must expose a :func:`fetch_insights` function returning a
``dict`` of metrics with the following keys: ``reach``,
``profile_views``, ``accounts_engaged``, ``website_clicks`` and
``total_interactions``. The transform modules expose a
:func:`transform_insights` function which accepts the raw dictionary
returned by the extractor and outputs a dictionary using the same
metric names.

See the documentation in individual modules for further details.
"""

from importlib import import_module  # noqa: F401
