"""
Extractors for the social media ETL pipeline.

Each extractor module should define a :func:`fetch_insights` function
which connects to the appropriate API, retrieves the desired metrics
and returns them as a dictionary. The dictionary keys should match the
standardised set defined across the project:

* ``reach`` – an integer representing the number of unique accounts
  reached or impressions served during the period.
* ``profile_views`` – an integer representing the number of profile
  views.
* ``accounts_engaged`` – an integer representing the count of
  engagements/interactions.
* ``website_clicks`` – an integer representing the number of times
  users clicked a website or link.
* ``total_interactions`` – an integer summarising all interactions
  (likes, comments, shares, etc.).

If a platform does not provide a metric, the extractor should set a
value of zero for that field. For example, if Twitter (X) does not
expose profile views, ``profile_views`` should be ``0`` in the
returned dictionary.
"""
