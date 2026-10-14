import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


def database_url() -> str:
    return os.environ["DATABASE_URL"]


@contextmanager
def connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        conn.execute("SET lock_timeout = '3s'")
        conn.execute("SET statement_timeout = '5s'")
        yield conn


def migrate() -> None:
    with connection() as conn:
        for migration in sorted(Path("migrations").glob("*.sql")):
            conn.execute(migration.read_text())


if __name__ == "__main__":
    migrate()
