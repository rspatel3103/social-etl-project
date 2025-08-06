"""
Data transformers for the ETL pipeline.

Transformers take the raw output of an extractor and normalise it to
the standard set of metrics expected by the downstream loader. In
many cases the extractor will already produce data in the desired
format, but separating transformation into its own module allows for
more complex mappings and calculations (e.g. aggregating multiple
fields, renaming keys or computing derived metrics).

Each module in this package should define a single function
:func:`transform_insights` which accepts a dictionary (the raw data
returned by the corresponding extractor) and returns a new
dictionary with the keys ``reach``, ``profile_views``,
``accounts_engaged``, ``website_clicks`` and ``total_interactions``.

If a metric is missing in the input, it must be supplied with a
default value (usually zero) in the output.
"""
