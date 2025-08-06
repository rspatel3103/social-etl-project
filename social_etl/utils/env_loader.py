"""
Environment loader for the ETL pipeline.

Many configuration values in this project are secrets or deployment
specific (API keys, account identifiers, database connection strings). To
avoid committing sensitive information into version control, these
values should be defined in a local ``.env`` file placed at the root of
the repository. Each line in this file must follow the ``KEY=value``
format. Lines beginning with ``#`` are treated as comments and
ignored. If a key is already present in ``os.environ`` then the value
from the environment is left unchanged to allow environment variables
to override the file.

Example ``.env``::

    # Instagram API credentials
    INSTAGRAM_ACCESS_TOKEN=EAAC...redacted...
    INSTAGRAM_ACCOUNT_ID=17841449129086190

    # LinkedIn API credentials
    LINKEDIN_ACCESS_TOKEN=...your token...

    # SQL Server connection string
    SQL_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=mydb;UID=user;PWD=pass

The :func:`load_env` function can be called at the start of your
program to populate ``os.environ`` with these values::

    from social_etl.utils.env_loader import load_env
    load_env()  # reads ``.env`` from current working directory
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_env(env_file: Optional[str] = None) -> None:
    """Load environment variables from a ``.env`` file.

    This function will read key/value pairs from the provided ``env_file``
    and populate ``os.environ`` with any keys that are not already
    defined. If ``env_file`` is omitted, it defaults to ``.env`` in
    the current working directory. Lines beginning with ``#`` are
    ignored, as are blank lines. Whitespace surrounding keys and
    values is stripped.

    Parameters
    ----------
    env_file : str or None
        Path to the environment file. If ``None`` (the default), the
        function looks for a file named ``.env`` in the current
        directory.

    Examples
    --------
    >>> load_env()  # doctest: +SKIP
    >>> os.getenv("INSTAGRAM_ACCESS_TOKEN")
    'EAAC...'
    """
    if env_file is None:
        env_file = ".env"

    path = Path(env_file)
    if not path.exists():
        # If the file doesn't exist, there is nothing to load. We
        # silently return to allow for optional configuration files.
        return

    with path.open() as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            # Only set the variable if it isn't already defined. This
            # allows environment variables to override values from the
            # file, which can be useful for CI/CD pipelines.
            if key and key not in os.environ:
                os.environ[key] = value
