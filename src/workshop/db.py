"""Database access for the workshop tools.

Two things live here rather than in the server, because both are decisions
rather than plumbing.

The first is that read access and write access are different connections.
`connect()` opens the database read-only, so a mistake in a SELECT physically
cannot modify data - SQLite refuses the write at the driver level rather than
trusting the query to be harmless. Only `connect(write=True)` can change
anything, and exactly one tool asks for it.

The second is where the database file lives. It is resolved once, here, and
can be pointed somewhere else with the WORKSHOP_DB environment variable -
which is what the test suite does to run against a throwaway copy.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

#: src/workshop/db.py -> src/workshop -> src -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: Set WORKSHOP_DB to run against a different database (the tests do this).
DB_ENV_VAR = "WORKSHOP_DB"


def database_path() -> Path:
    """Where the workshop database lives."""
    override = os.environ.get(DB_ENV_VAR)
    if override:
        return Path(override)
    return _PROJECT_ROOT / "garage.db"


def connect(write: bool = False) -> sqlite3.Connection:
    """Open the workshop database.

    Read tools open it read-only so that a bug in a query cannot modify
    anything. Only `add_job_note` passes write=True.
    """
    path = database_path()
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run 'uv run workshop-seed' first.")
    if write:
        con = sqlite3.connect(path)
    else:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a read-only query and return plain dictionaries."""
    con = connect()
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()
