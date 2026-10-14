import hashlib
import json
import os
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def snapshot(url: str) -> dict[str, Any]:
    result = {}
    with psycopg.connect(url, row_factory=dict_row) as conn:
        tables = conn.execute(
            "SELECT schemaname,tablename FROM pg_tables WHERE schemaname IN ('public','sandbox') "
            "ORDER BY schemaname,tablename"
        ).fetchall()
        for table in tables:
            rows = conn.execute(
                sql.SQL("SELECT * FROM {}.{}").format(
                    sql.Identifier(table["schemaname"]),
                    sql.Identifier(table["tablename"]),
                )
            ).fetchall()
            serialized = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
            result[f"{table['schemaname']}.{table['tablename']}"] = {
                "count": len(rows),
                "sha256": hashlib.sha256("\n".join(serialized).encode()).hexdigest(),
            }
    return result


if __name__ == "__main__":
    destination = os.environ["RESTORE_DATABASE_URL"]
    if not destination.endswith("workbench_restore_test"):
        raise RuntimeError("Restore verification requires an isolated restore database")
    original = snapshot(os.environ["DATABASE_URL"])
    restored = snapshot(destination)
    assert original == restored, "Restored contents differ"
    assert original["sandbox.effects"]["count"] > 0
    assert original["public.checkpoints"]["count"] > 0
    print(json.dumps({"verified": True, "tables": restored}, indent=2))
