"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from workshop.db import DB_ENV_VAR
from workshop.seed import build_database


@pytest.fixture(autouse=True)
def workshop_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A freshly seeded database for every test.

    Rebuilding per test rather than per session costs a few milliseconds and
    buys complete independence: the write tests cannot leak a note into the
    read tests, and any single test can be run on its own and still pass.
    """
    path = tmp_path / "garage.db"
    build_database(path)
    monkeypatch.setenv(DB_ENV_VAR, str(path))
    yield path
