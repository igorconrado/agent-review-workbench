"""Single-process demonstration worker; PostgreSQL remains authoritative."""

import json
import time

from workbench.graph import run_graph
from workbench.store import connection


def tick() -> None:
    with connection() as conn:
        pending = conn.execute(
            "SELECT id,decision_by FROM cases WHERE status IN ('approved','uncertain') "
            "ORDER BY created_at LIMIT 20"
        ).fetchall()
    for case in pending:
        case_id = str(case["id"])
        try:
            run_graph(case["decision_by"], case_id, resume=True)
            print(json.dumps({"event": "worker_completed", "case_id": case_id}), flush=True)
        except Exception as error:
            print(
                json.dumps(
                    {
                        "event": "worker_failed",
                        "case_id": case_id,
                        "error_type": type(error).__name__,
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    while True:
        tick()
        time.sleep(5)
