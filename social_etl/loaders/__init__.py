"""
Data loaders for the ETL pipeline.

Loaders are responsible for persisting transformed data into a
destination system. In this project the primary destination is a
Microsoft SQL Server database. The loader implementation is
centralised in :mod:`social_etl.loaders.sql_loader`, which exposes
functions for ensuring the target table exists and for performing an
upsert operation to insert or update daily records.

Additional loaders (e.g. for CSV files, cloud data warehouses or
NoSQL databases) could be added here in the future. Each loader
should expose a single function that accepts the transformed data and
the platform name, and performs the write.
"""
